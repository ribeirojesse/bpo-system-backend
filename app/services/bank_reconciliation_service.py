import re

import unicodedata

from collections import Counter

from datetime import timedelta

from decimal import Decimal

from difflib import SequenceMatcher

from fastapi import HTTPException

from app.models.bank_transaction import BankTransaction

from app.models.financial_contact import FinancialContact

from app.repositories.bank_transaction_repository import (
    BankTransactionRepository
)

from app.repositories.accounts_payable_repository import (
    AccountsPayableRepository
)

from app.repositories.accounts_receivable_repository import (
    AccountsReceivableRepository
)

from app.repositories.bank_reconciliation_repository import (
    BankReconciliationRepository
)

from app.repositories.financial_contact_repository import (
    FinancialContactRepository
)

from app.repositories.expense_category_repository import (
    ExpenseCategoryRepository
)

from app.repositories.expense_subcategory_repository import (
    ExpenseSubcategoryRepository
)

from app.models.accounts_payable import AccountsPayable

from app.models.accounts_receivable import AccountsReceivable

from app.models.bank_reconciliation import BankReconciliation


class BankReconciliationService:

    # Tolerância para divergência entre o valor conciliado e o valor
    # real da transação/título (evita rejeitar por arredondamento de
    # centavos, mas bloqueia conciliações com valores muito diferentes).
    TOLERANCIA = Decimal("0.01")

    # Tolerância de valor usada só pra ENCONTRAR candidatos na tela de
    # Conciliação (nunca pra vincular sozinho — isso continua exigindo um
    # clique do usuário em "Conciliar"). Cobre casos comuns como boleto
    # pago com juros/desconto ou taxa de cartão descontada na hora: até
    # 5% de diferença pro valor do lançamento ainda entra como candidato,
    # combinado com a descrição pra não virar uma sugestão qualquer.
    TOLERANCIA_VALOR_PERCENTUAL = Decimal("0.05")

    # Mesma janela usada pela conciliação automática (AutoReconciliationService):
    # um lançamento com o mesmo valor e vencimento até 5 dias de distância da
    # transação ainda entra como sugestão (confiança "PROXIMO" — o "Quase lá"
    # do Conta Azul); vencimento exatamente igual vira "EXATO" ("Encontramos").
    TOLERANCIA_DIAS_SUGESTAO = 5

    # Quando não há lançamento com valor+data batendo bem, ainda vale
    # sugerir um candidato pela DESCRIÇÃO parecida (ex.: mesmo fornecedor
    # recorrente, mas com vencimento fora da janela de 5 dias, ou valor
    # dentro da tolerância de 5% mas não idêntico) — vira a confiança
    # "PARECIDO", abaixo de "PROXIMO". Também é o piso exigido pra aceitar
    # qualquer candidato com valor APROXIMADO (não exatamente igual):
    # valor parecido sozinho, sem a descrição bater, não é o suficiente.
    # Limiar calibrado contra descrições reais de extrato: acima disso,
    # na prática só nomes de fornecedor realmente iguais (ignorando
    # números de documento/referência, que variam a cada lançamento)
    # passam.
    SIMILARIDADE_MINIMA = 0.55

    # Pra sugerir contato/categoria mais usados em transações com
    # descrição parecida (quando não há nenhum lançamento candidato pra
    # vincular direto), olhamos até esse tanto de lançamentos históricos
    # mais recentes — suficiente pra pegar o padrão sem escanear a tabela
    # inteira em clientes com anos de histórico.
    HISTORICO_LIMITE = 300

    # Prefixos comuns de extrato bancário brasileiro que não ajudam em
    # nada a identificar o fornecedor (o nome vem DEPOIS) — atrapalham a
    # comparação de similaridade porque são iguais em lançamentos de
    # fornecedores completamente diferentes. Comparados já sem acento,
    # minúsculo e sem pontuação, então aqui também ficam assim.
    _PREFIXOS_BANCARIOS = (
        "pix recebido de",
        "pix recebido",
        "pix enviado para",
        "pix enviado",
        "ted recebida de",
        "ted recebida",
        "ted recebido de",
        "ted recebido",
        "ted enviada para",
        "ted enviada",
        "ted enviado para",
        "ted enviado",
        "doc recebido de",
        "doc recebido",
        "doc enviado para",
        "doc enviado",
        "transferencia recebida de",
        "transferencia recebida",
        "transferencia enviada para",
        "transferencia enviada",
        "pagamento de boleto",
        "pagamento efetuado",
        "compra no debito",
        "compra no credito",
    )

    # Sufixos societários — o mesmo fornecedor pode aparecer cadastrado
    # como "Fulano Comercio Ltda" e no extrato só como "FULANO COMERCIO",
    # ou vice-versa.
    _SUFIXOS_SOCIETARIOS = (
        " ltda me",
        " eireli me",
        " ltda",
        " eireli",
        " mei",
        " s a",
        " sa",
        " me",
    )

    @staticmethod
    def _normalizar_texto(texto):
        """Minúsculas, sem acento, sem pontuação e sem números — números
        de documento/referência variam a cada lançamento do mesmo
        fornecedor recorrente, e atrapalhariam a comparação de
        similaridade do nome/descrição em si (ex.: "TED FULANO LTDA
        001234" vs "TED FULANO LTDA 009876"). Também tira prefixos de
        extrato bancário ("PIX RECEBIDO DE") e sufixos societários
        ("LTDA", "ME") que são ruído pra comparar o nome do fornecedor
        em si."""

        texto = (texto or "").strip()

        # Remove acentos (NFKD separa a letra do acento, depois
        # descartamos só os caracteres de acentuação combinante).
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(
            c for c in texto if not unicodedata.combining(c)
        )

        texto = texto.lower()

        texto = re.sub(r"\d+", "", texto)

        # Pontuação/símbolos viram espaço (não some, pra não colar duas
        # palavras: "TED/DOC" -> "ted doc", não "teddoc").
        texto = re.sub(r"[^a-z\s]", " ", texto)

        texto = re.sub(r"\s+", " ", texto).strip()

        for prefixo in (
            BankReconciliationService._PREFIXOS_BANCARIOS
        ):
            if texto.startswith(prefixo):
                texto = texto[len(prefixo):].strip()
                break

        for sufixo in (
            BankReconciliationService._SUFIXOS_SOCIETARIOS
        ):
            if texto.endswith(sufixo):
                texto = texto[:-len(sufixo)].strip()
                break

        return texto

    @staticmethod
    def _similaridade_descricao(a, b):

        a = BankReconciliationService._normalizar_texto(a)

        b = BankReconciliationService._normalizar_texto(b)

        if not a or not b:
            return 0.0

        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def _sugerir_contato_categoria_por_historico(
        db,
        current_user,
        transaction,
        Model
    ):
        """Quando não existe nenhum lançamento candidato pra vincular
        (nem por valor+data, nem por descrição parecida), ainda dá pra
        ajudar: olha o histórico de lançamentos desse cliente com
        descrição parecida com a da transação e sugere o contato e a
        categoria mais usados nesses casos — só pra pré-preencher o
        formulário de "Criar lançamento", nunca pra vincular sozinho."""

        historico = (
            db.query(Model)
            .filter(
                Model.tenant_id
                == current_user.tenant_id,

                Model.client_id
                == transaction.client_id,
            )
            .order_by(
                Model.vencimento.desc()
            )
            .limit(
                BankReconciliationService
                .HISTORICO_LIMITE
            )
            .all()
        )

        candidatos = [
            item for item in historico
            if BankReconciliationService
            ._similaridade_descricao(
                transaction.descricao,
                item.descricao
            )
            >= BankReconciliationService
            .SIMILARIDADE_MINIMA
        ]

        if not candidatos:
            return None, None, None

        contato_mais_usado = Counter(
            item.financial_contact_id
            for item in candidatos
        ).most_common(1)[0][0]

        # Categoria/subcategoria mais usada especificamente entre os
        # lançamentos desse mesmo contato (não do grupo todo) — mais
        # preciso do que só "a categoria mais comum entre parecidos",
        # já que fornecedores diferentes tendem a cair em categorias
        # diferentes mesmo com descrição de transação parecida.
        do_contato = [
            item for item in candidatos
            if item.financial_contact_id
            == contato_mais_usado
        ]

        categoria_mais_usada = Counter(
            item.category_id
            for item in do_contato
        ).most_common(1)[0][0]

        subcategorias_da_categoria = [
            item.subcategory_id
            for item in do_contato
            if item.category_id
            == categoria_mais_usada
            and item.subcategory_id
        ]

        subcategoria_mais_usada = (
            Counter(
                subcategorias_da_categoria
            ).most_common(1)[0][0]
            if subcategorias_da_categoria
            else None
        )

        return (
            contato_mais_usado,
            categoria_mais_usada,
            subcategoria_mais_usada,
        )

    @staticmethod
    def _sugerir_contato_por_nome(
        db,
        current_user,
        transaction
    ):
        """Último recurso, quando nem um lançamento candidato (por valor
        e data) nem o histórico de lançamentos parecidos encontrou nada
        — o que acontece sempre que o fornecedor é novo (cadastrado
        formalmente ou digitado na hora, na tela de Conciliação, ambos
        viram uma linha real em FinancialContact) e ainda não tem nenhum
        lançamento anterior pra comparar. Aqui comparamos a descrição da
        transação direto com o NOME de cada fornecedor já cadastrado
        desse cliente — sem depender de já ter histórico nenhum. Só
        sugere o contato pra pré-preencher o formulário; categoria e
        subcategoria ficam em branco."""

        contatos = (
            db.query(FinancialContact)
            .filter(
                FinancialContact.tenant_id
                == current_user.tenant_id,

                FinancialContact.client_id
                == transaction.client_id,

                FinancialContact.ativo
                == True,  # noqa: E712
            )
            .all()
        )

        melhor_contato = None
        melhor_similaridade = 0.0

        for contato in contatos:

            similaridade = (
                BankReconciliationService
                ._similaridade_descricao(
                    transaction.descricao,
                    contato.nome
                )
            )

            if similaridade > melhor_similaridade:
                melhor_similaridade = similaridade
                melhor_contato = contato

        if (
            melhor_contato
            and melhor_similaridade
            >= BankReconciliationService.SIMILARIDADE_MINIMA
        ):
            return melhor_contato.id

        return None

    @staticmethod
    def _dentro_tolerancia_valor(diferenca, valor_base):
        """Aceita uma divergência de valor tanto pelo piso fixo
        (TOLERANCIA, arredondamento de centavos) quanto pela tolerância
        percentual (TOLERANCIA_VALOR_PERCENTUAL, 5% do valor do
        lançamento) — a mesma usada em get_suggestions pra sugerir
        candidatos com valor aproximado. Sem isso, um match PROXIMO ou
        PARECIDO com valor um pouco diferente (ex.: boleto pago com
        desconto) seria sugerido na tela de Conciliação e depois
        rejeitado ao clicar em "Conciliar"."""

        valor_base = Decimal(str(valor_base))

        tolerancia_percentual = (
            valor_base
            * BankReconciliationService
            .TOLERANCIA_VALOR_PERCENTUAL
        )

        limite = max(
            BankReconciliationService.TOLERANCIA,
            tolerancia_percentual,
        )

        return diferenca <= limite

    @staticmethod
    def create_reconciliation(
        db,
        current_user,
        data
    ):

        transaction = BankTransactionRepository.get_by_id(
            db,
            current_user.tenant_id,
            data.bank_transaction_id
        )

        if not transaction:
            raise HTTPException(
                status_code=404,
                detail="Transação não encontrada"
            )

        # BLOQUEIA FOLHA JÁ PROCESSADA
        if transaction.processado:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa transação já foi "
                    "processada via folha "
                    "de pagamento"
                )
            )

        # BLOQUEIA TRANSAÇÃO JÁ CONCILIADA
        if transaction.conciliado:

            raise HTTPException(
                status_code=400,
                detail="Essa transação já foi conciliada"
            )

        if (
            not data.accounts_payable_id
            and
            not data.accounts_receivable_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Informe conta a pagar "
                    "ou conta a receber"
                )
            )

        # VALIDA DIVERGÊNCIA ENTRE VALOR CONCILIADO E VALOR DA TRANSAÇÃO
        diferenca_transacao = abs(
            Decimal(str(data.valor_conciliado))
            - Decimal(str(transaction.valor))
        )

        if diferenca_transacao > BankReconciliationService.TOLERANCIA:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Valor conciliado diverge do "
                    "valor da transação bancária"
                )
            )

        if data.accounts_payable_id:

            payable = AccountsPayableRepository.get_by_id(
                db,
                current_user.tenant_id,
                data.accounts_payable_id
            )

            if not payable:
                raise HTTPException(
                    status_code=404,
                    detail="Conta a pagar não encontrada"
                )

            # VALIDA MESMO CLIENTE DA TRANSAÇÃO
            if payable.client_id != transaction.client_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A conta a pagar pertence a um "
                        "cliente diferente da transação"
                    )
                )

            diferenca_titulo = abs(
                Decimal(str(data.valor_conciliado))
                - Decimal(str(payable.valor))
            )

            if not (
                BankReconciliationService
                ._dentro_tolerancia_valor(
                    diferenca_titulo,
                    payable.valor
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Valor conciliado diverge do "
                        "valor da conta a pagar"
                    )
                )

            payable.status = "PAGO"

            if not payable.data_pagamento:
                payable.data_pagamento = (
                    data.data_conciliacao
                )

        if data.accounts_receivable_id:

            receivable = (
                AccountsReceivableRepository.get_by_id(
                    db,
                    current_user.tenant_id,
                    data.accounts_receivable_id
                )
            )

            if not receivable:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Conta a receber não encontrada"
                    )
                )

            # VALIDA MESMO CLIENTE DA TRANSAÇÃO
            if receivable.client_id != transaction.client_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A conta a receber pertence a um "
                        "cliente diferente da transação"
                    )
                )

            diferenca_titulo = abs(
                Decimal(str(data.valor_conciliado))
                - Decimal(str(receivable.valor))
            )

            if not (
                BankReconciliationService
                ._dentro_tolerancia_valor(
                    diferenca_titulo,
                    receivable.valor
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Valor conciliado diverge do "
                        "valor da conta a receber"
                    )
                )

            receivable.status = "RECEBIDO"

            if not receivable.data_recebimento:
                receivable.data_recebimento = (
                    data.data_conciliacao
                )

        transaction.conciliado = True

        payload = data.model_dump()

        payload["tenant_id"] = current_user.tenant_id

        reconciliation = (
            BankReconciliationRepository.create(
                db,
                payload
            )
        )

        db.commit()

        return reconciliation

    @staticmethod
    def create_reconciliation_from_transaction(
        db,
        current_user,
        transaction_id,
        data
    ):
        """Concilia uma transação bancária e, no mesmo passo atômico, cria
        o lançamento financeiro (conta a pagar/receber) correspondente já
        como PAGO/RECEBIDO.

        Esse é o fluxo padrão de "Conciliar" no frontend, e substitui a
        sequência antiga de 3 chamadas separadas (criar conta → marcar
        transação como conciliada → registrar a conciliação), que tinha um
        bug de ordenação: a transação era marcada como conciliada ANTES de
        registrar a conciliação, então o registro de histórico sempre
        falhava (a validação abaixo já barrava por "transação já
        conciliada") e a conta a pagar/receber criada ficava para sempre
        com o status padrão PENDENTE — obrigando quem usa o sistema a ir
        até Contas a Pagar/Receber e confirmar manualmente um pagamento
        que, na prática, o extrato bancário já mostrava como efetivado.
        Fazendo tudo em uma única transação de banco de dados, ou dá tudo
        certo, ou nada é gravado.
        """

        transaction = BankTransactionRepository.get_by_id(
            db,
            current_user.tenant_id,
            transaction_id
        )

        if not transaction:
            raise HTTPException(
                status_code=404,
                detail="Transação não encontrada"
            )

        if transaction.processado:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa transação já foi "
                    "processada via folha "
                    "de pagamento"
                )
            )

        if transaction.conciliado:
            raise HTTPException(
                status_code=400,
                detail="Essa transação já foi conciliada"
            )

        if transaction.ignorada:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa transação foi arquivada — "
                    "reabra-a antes de conciliar"
                )
            )

        contact = FinancialContactRepository.get_by_id(
            db,
            current_user.tenant_id,
            data.financial_contact_id
        )

        if not contact:
            raise HTTPException(
                status_code=404,
                detail="Contato não encontrado"
            )

        category = ExpenseCategoryRepository.get_by_id(
            db,
            current_user.tenant_id,
            data.category_id
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Categoria não encontrada"
            )

        if data.subcategory_id:

            subcategory = (
                ExpenseSubcategoryRepository.get_by_id(
                    db,
                    current_user.tenant_id,
                    data.subcategory_id
                )
            )

            if not subcategory:
                raise HTTPException(
                    status_code=404,
                    detail="Subcategoria não encontrada"
                )

        is_credito = transaction.tipo == "CREDITO"

        entry_fields = dict(
            tenant_id=current_user.tenant_id,
            client_id=transaction.client_id,
            financial_contact_id=data.financial_contact_id,
            category_id=data.category_id,
            subcategory_id=data.subcategory_id,
            descricao=transaction.descricao,
            valor=transaction.valor,
            vencimento=transaction.data_transacao,
            competencia=data.competencia,
            observacao=data.observacao,
        )

        if is_credito:
            entry = AccountsReceivable(
                **entry_fields,
                status="RECEBIDO",
                data_recebimento=transaction.data_transacao,
            )
        else:
            entry = AccountsPayable(
                **entry_fields,
                status="PAGO",
                data_pagamento=transaction.data_transacao,
            )

        db.add(entry)

        db.flush()

        transaction.conciliado = True

        reconciliation = BankReconciliation(
            tenant_id=current_user.tenant_id,
            bank_transaction_id=transaction.id,
            accounts_payable_id=(
                None if is_credito else entry.id
            ),
            accounts_receivable_id=(
                entry.id if is_credito else None
            ),
            valor_conciliado=transaction.valor,
            data_conciliacao=transaction.data_transacao,
            observacao=data.observacao,
        )

        db.add(reconciliation)

        db.commit()

        db.refresh(reconciliation)

        return reconciliation

    @staticmethod
    def get_suggestions(
        db,
        current_user
    ):
        """Para cada transação bancária ainda não conciliada (e não
        ignorada/processada), procura um lançamento já existente — conta
        a pagar ou a receber, ainda não vinculado a nenhuma conciliação —
        que pareça corresponder a ela: mesmo cliente, valor igual ou
        dentro de 5% de diferença, e:
          - vencimento igual → EXATO ("Encontramos")
          - valor exato e vencimento até 5 dias de distância, OU valor
            aproximado (dentro dos 5%) no mesmo dia com a descrição
            batendo → PROXIMO ("Quase lá")
          - valor exato com descrição parecida (mesmo fora da janela de
            5 dias), OU valor aproximado com descrição parecida (mesmo
            fora do mesmo dia) → PARECIDO
        Valor só aproximado SEM a descrição bater nunca vira sugestão —
        evita coincidência de dois lançamentos com valor parecido por
        acaso. Quando não há candidato nenhum pra vincular, ainda
        sugerimos contato/categoria pra pré-preencher o formulário de
        "Criar lançamento" (nunca pra vincular sozinho): primeiro pelo
        contato/categoria mais usados em lançamentos antigos com
        descrição parecida; se não achar nada (fornecedor novo, sem
        histórico ainda — cadastrado formalmente ou só digitado na tela
        de Conciliação), comparamos a descrição direto com o nome dos
        fornecedores já cadastrados desse cliente.

        É a base da tela de Conciliação no estilo Conta Azul: em vez de
        só listar a transação e pedir pra preencher tudo de novo, já
        mostra o melhor candidato ao lado (quando existe) pra conciliar
        num clique só."""

        transactions = (
            db.query(BankTransaction)
            .filter(
                BankTransaction.tenant_id
                == current_user.tenant_id,

                BankTransaction.conciliado
                == False,  # noqa: E712

                BankTransaction.processado
                == False,  # noqa: E712

                BankTransaction.ignorada
                == False,  # noqa: E712
            )
            .all()
        )

        # Lançamentos que já estão vinculados a alguma conciliação não
        # devem ser sugeridos de novo pra outra transação.
        payable_ids_vinculados = {
            row[0]
            for row in db.query(
                BankReconciliation.accounts_payable_id
            ).filter(
                BankReconciliation.tenant_id
                == current_user.tenant_id,

                BankReconciliation.accounts_payable_id
                .isnot(None),
            ).all()
        }

        receivable_ids_vinculados = {
            row[0]
            for row in db.query(
                BankReconciliation.accounts_receivable_id
            ).filter(
                BankReconciliation.tenant_id
                == current_user.tenant_id,

                BankReconciliation.accounts_receivable_id
                .isnot(None),
            ).all()
        }

        results = []

        for transaction in transactions:

            match = None

            is_credito = (
                transaction.tipo == "CREDITO"
            )

            Model = (
                AccountsReceivable
                if is_credito
                else AccountsPayable
            )

            tipo_match = (
                "RECEIVABLE"
                if is_credito
                else "PAYABLE"
            )

            ids_vinculados = (
                receivable_ids_vinculados
                if is_credito
                else payable_ids_vinculados
            )

            # Valor exatamente igual continua sendo o melhor caso, mas
            # agora também aceitamos candidatos com valor dentro de 5%
            # (TOLERANCIA_VALOR_PERCENTUAL) — cobre juros/desconto de
            # boleto, taxa de cartão descontada etc. Buscamos já num
            # intervalo pra não escanear lançamentos com valor muito
            # diferente à toa; o filtro fino (exigir descrição parecida
            # quando o valor não é exato) acontece no loop abaixo.
            valor_transacao = Decimal(str(transaction.valor))

            tolerancia_valor = (
                valor_transacao
                * BankReconciliationService
                .TOLERANCIA_VALOR_PERCENTUAL
            )

            valor_minimo = valor_transacao - tolerancia_valor
            valor_maximo = valor_transacao + tolerancia_valor

            candidatos = (
                db.query(Model)
                .filter(
                    Model.tenant_id
                    == current_user.tenant_id,

                    Model.client_id
                    == transaction.client_id,

                    Model.valor
                    >= valor_minimo,

                    Model.valor
                    <= valor_maximo,
                )
                .all()
            )

            avaliados = []

            for item in candidatos:

                if item.id in ids_vinculados:
                    continue

                valor_exato = (
                    Decimal(str(item.valor))
                    == valor_transacao
                )

                diferenca_valor = abs(
                    Decimal(str(item.valor))
                    - valor_transacao
                )

                dias = abs(
                    (
                        item.vencimento
                        - transaction.data_transacao
                    ).days
                )

                similaridade = (
                    BankReconciliationService
                    ._similaridade_descricao(
                        transaction.descricao,
                        item.descricao
                    )
                )

                descricao_bate = (
                    similaridade
                    >= BankReconciliationService
                    .SIMILARIDADE_MINIMA
                )

                # Valor só aproximado (não exato) sem a descrição bater
                # é coincidência demais pra virar sugestão — dois
                # lançamentos de fornecedores diferentes podem ter
                # valores parecidos por acaso.
                if not valor_exato and not descricao_bate:
                    continue

                if valor_exato and dias == 0:
                    confianca = "EXATO"

                elif (
                    valor_exato
                    and dias
                    <= BankReconciliationService
                    .TOLERANCIA_DIAS_SUGESTAO
                ):
                    confianca = "PROXIMO"

                elif (
                    not valor_exato
                    and dias == 0
                    and descricao_bate
                ):
                    # Mesmo dia e descrição bate — só o valor variou um
                    # pouco (juros, desconto, taxa): quase tão confiável
                    # quanto EXATO.
                    confianca = "PROXIMO"

                elif descricao_bate:
                    confianca = "PARECIDO"

                else:
                    continue

                avaliados.append((
                    item,
                    dias,
                    confianca,
                    diferenca_valor,
                    similaridade,
                ))

            if avaliados:

                ordem_confianca = {
                    "EXATO": 0,
                    "PROXIMO": 1,
                    "PARECIDO": 2,
                }

                (
                    melhor,
                    _dias_melhor,
                    confianca,
                    _diferenca_valor_melhor,
                    _similaridade_melhor,
                ) = min(
                    avaliados,
                    key=lambda avaliado: (
                        ordem_confianca[
                            avaliado[2]
                        ],
                        avaliado[3],  # diferença de valor
                        avaliado[1],  # dias
                        -avaliado[4],  # similaridade (maior é melhor)
                    )
                )

                match = {
                    "tipo": tipo_match,
                    "id": melhor.id,
                    "descricao": melhor.descricao,
                    "valor": melhor.valor,
                    "vencimento": melhor.vencimento,
                    "financial_contact_id":
                        melhor.financial_contact_id,
                    "category_id":
                        melhor.category_id,
                    "subcategory_id":
                        melhor.subcategory_id,
                    "confianca": confianca,
                }

            sugestao_contato = None
            sugestao_categoria = None
            sugestao_subcategoria = None

            if not match:

                (
                    sugestao_contato,
                    sugestao_categoria,
                    sugestao_subcategoria,
                ) = (
                    BankReconciliationService
                    ._sugerir_contato_categoria_por_historico(
                        db,
                        current_user,
                        transaction,
                        Model
                    )
                )

                if not sugestao_contato:

                    sugestao_contato = (
                        BankReconciliationService
                        ._sugerir_contato_por_nome(
                            db,
                            current_user,
                            transaction
                        )
                    )

            results.append({
                "transaction_id": transaction.id,
                "match": match,
                "sugestao_financial_contact_id":
                    sugestao_contato,
                "sugestao_category_id":
                    sugestao_categoria,
                "sugestao_subcategory_id":
                    sugestao_subcategoria,
            })

        return results

    @staticmethod
    def get_reconciliations(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return (
            BankReconciliationRepository.get_all(
                db,
                current_user.tenant_id,
                skip,
                limit
            )
        )

    @staticmethod
    def get_reconciliation(
        db,
        current_user,
        reconciliation_id
    ):

        reconciliation = (
            BankReconciliationRepository.get_by_id(
                db,
                current_user.tenant_id,
                reconciliation_id
            )
        )

        if not reconciliation:
            raise HTTPException(
                status_code=404,
                detail="Conciliação não encontrada"
            )

        return reconciliation

    @staticmethod
    def delete_reconciliation(
        db,
        current_user,
        reconciliation_id
    ):
        """Desfaz uma conciliação: remove só o VÍNCULO com o extrato
        bancário, marcando a transação como não conciliada de novo (ela
        volta a aparecer em "não conciliado" na tela de Conciliação,
        onde pode ser religada ou re-sugerida). O lançamento (conta a
        pagar/receber) continua PAGO/RECEBIDO como estava — igual ao
        Conta Azul, "pago" e "conciliado" são coisas independentes; o
        dinheiro já saiu/entrou de verdade, só a conferência com o banco
        é que está sendo desfeita.

        Antes isso reabria o título como PENDENTE (zerando
        data_pagamento/data_recebimento), o que reintroduzia bem a etapa
        de "confirmar pagamento" que a rodada 1 tinha eliminado: o
        lançamento virava ATRASADO se o vencimento já tivesse passado, e
        aparecia de novo o botão de marcar como pago manualmente — só que
        agora em Contas a Pagar/Receber, em vez de na Conciliação."""

        reconciliation = (
            BankReconciliationService.get_reconciliation(
                db,
                current_user,
                reconciliation_id
            )
        )

        transaction = BankTransactionRepository.get_by_id(
            db,
            current_user.tenant_id,
            reconciliation.bank_transaction_id
        )

        if transaction:
            transaction.conciliado = False

        BankReconciliationRepository.delete(
            db,
            reconciliation
        )

        return {
            "message": (
                "Conciliação desfeita — a transação "
                "voltou para \"não conciliado\" na tela "
                "de Conciliação"
            )
        }
