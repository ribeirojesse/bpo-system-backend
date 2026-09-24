"""Sugestões de conciliação com IA (API do Claude).

Complementa a heurística de BankReconciliationService.get_suggestions,
que já resolve bem os casos "fáceis" (valor + data + descrição parecida).
A IA entra onde a heurística não acha nada ou só acha algo fraco:
descrição de extrato truncada/críptica, fornecedor que aparece com nome
diferente do cadastro, fornecedor novo, categoria que depende do padrão
histórico daquele cliente.

Princípios:
- Nada é conciliado sozinho: a sugestão só aparece na tela pro usuário
  aceitar ("Conciliar" / "Criar lançamento" já pré-preenchido).
- O modelo nunca vê UUIDs: cada fornecedor/categoria/lançamento/transação
  vira uma referência curta (F1, C2, L3, T4...). O que volta é traduzido
  de volta pelo backend a partir desses mapas — uma referência inventada
  simplesmente não existe no mapa e é descartada. Tudo é escopado por
  tenant + cliente antes de montar o contexto.
- CPF/CNPJ nas descrições do extrato são mascarados antes do envio.
- Resultado fica guardado em ai_reconciliation_suggestions (uma linha por
  transação), pra não pagar a IA de novo a cada abertura da tela.
"""

import logging
import re

from datetime import timedelta

from decimal import Decimal

from fastapi import HTTPException

from app.core.config import settings

from app.models.accounts_payable import AccountsPayable
from app.models.accounts_receivable import AccountsReceivable
from app.models.ai_reconciliation_suggestion import (
    AIReconciliationSuggestion
)
from app.models.bank_reconciliation import BankReconciliation
from app.models.bank_transaction import BankTransaction
from app.models.client import Client
from app.models.expense_category import ExpenseCategory
from app.models.expense_subcategory import ExpenseSubcategory
from app.models.financial_contact import FinancialContact
from app.models.payroll_item import PayrollItem

from app.services.ai_client import AIClient, AIError
from app.services.bank_reconciliation_service import (
    BankReconciliationService
)
from app.services.payroll_pdf_service import PayrollPDFService


logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """Você é assistente de conciliação bancária de um \
escritório de BPO financeiro brasileiro. Recebe, de UM cliente do \
escritório: fornecedores/clientes cadastrados, plano de categorias, \
lançamentos em aberto, exemplos de conciliações anteriores e uma lista de \
transações do extrato bancário ainda não conciliadas. Para cada transação, \
sugira como conciliá-la chamando a ferramenta uma única vez com todas as \
sugestões.

Como decidir:
1. Vincular a um lançamento existente (campo "lancamento", ref L...) \
só quando: o tipo bate (DEBITO com "A PAGAR", CREDITO com "A RECEBER"); o \
valor é igual ou até 5% diferente (juros, multa, desconto, tarifa); e a \
descrição/fornecedor é coerente. As datas podem diferir alguns dias. Cada \
lançamento pode ser usado no máximo uma vez.
2. Sem lançamento para vincular: indique o fornecedor/cliente cadastrado \
(ref F...) quando o nome no extrato corresponder — considere abreviações, \
nomes cortados, razão social x nome fantasia e prefixos bancários ("PIX \
ENVIADO", "TED", "PAG BOLETO", "DEB AUT"). Se claramente for alguém ainda \
não cadastrado, deixe "fornecedor" nulo e preencha "novo_fornecedor_nome" \
com um nome limpo e legível (sem prefixos bancários, números de documento \
ou CPF/CNPJ). Se não der para identificar, deixe os dois nulos.
3. Categoria/subcategoria: use somente refs listadas (C.../S...); a \
subcategoria precisa pertencer à categoria. Dê preferência ao padrão do \
histórico deste cliente. Se nenhuma servir, deixe nulo.
4. Competência (MM/AAAA): o mês a que a despesa/receita se refere. Use o \
mês indicado na descrição, se houver (ex.: "ALUGUEL AGO"); salários e \
pró-labore pagos no início do mês normalmente são do mês anterior; nos \
demais casos, o mês da transação.
5. Transferência entre contas do próprio cliente, aplicação/resgate de \
investimento ou estorno: não force fornecedor; diga isso na justificativa \
(o usuário pode "Ignorar" a transação).
6. "confianca": ALTA quando o nome e o padrão batem claramente; MEDIA \
quando é provável; BAIXA quando há pouca evidência. Prefira deixar campos \
nulos a chutar.
7. "justificativa": uma frase curta em português explicando o porquê, sem \
repetir CPF/CNPJ.
Nunca invente referências que não estejam na lista."""


_TOOL = {
    "name": "registrar_sugestoes",
    "description": (
        "Registra uma sugestão de conciliação para cada transação "
        "bancária recebida."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sugestoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "transacao": {
                            "type": "string",
                            "description": "Ref da transação, ex.: T1",
                        },
                        "lancamento": {"type": ["string", "null"]},
                        "fornecedor": {"type": ["string", "null"]},
                        "novo_fornecedor_nome": {"type": ["string", "null"]},
                        "categoria": {"type": ["string", "null"]},
                        "subcategoria": {"type": ["string", "null"]},
                        "competencia": {"type": ["string", "null"]},
                        "confianca": {
                            "type": "string",
                            "enum": ["ALTA", "MEDIA", "BAIXA"],
                        },
                        "justificativa": {"type": "string"},
                    },
                    "required": [
                        "transacao",
                        "confianca",
                        "justificativa",
                    ],
                },
            }
        },
        "required": ["sugestoes"],
    },
}


class AIReconciliationService:

    # Transações por chamada à IA (e por requisição HTTP — mantém cada
    # requisição bem abaixo do timeout de 60s do nginx). O frontend chama
    # de novo enquanto "restantes" > 0.
    LOTE_MAXIMO = 20

    HISTORICO_EXEMPLOS = 60

    CANDIDATOS_MAXIMO = 150

    CONTATOS_MAXIMO = 400

    # Lançamentos candidatos: vencimento até N dias antes/depois das
    # transações do lote.
    JANELA_DIAS_CANDIDATOS = 60

    CONFIANCAS = ("ALTA", "MEDIA", "BAIXA")

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def mascarar_documentos(texto):
        """Troca CNPJ/CPF por marcadores antes de mandar pra IA (LGPD)."""

        texto = texto or ""

        texto = re.sub(
            r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b",
            "[CNPJ]",
            texto
        )

        texto = re.sub(
            r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",
            "[CPF]",
            texto
        )

        return texto

    @staticmethod
    def _limpar_texto(texto, limite=120):

        texto = re.sub(r"[\r\n|]+", " ", str(texto or ""))

        return re.sub(r"\s+", " ", texto).strip()[:limite]

    @staticmethod
    def _ids_vinculados(db, tenant_id):

        payables = {
            row[0]
            for row in db.query(
                BankReconciliation.accounts_payable_id
            ).filter(
                BankReconciliation.tenant_id == tenant_id,
                BankReconciliation.accounts_payable_id.isnot(None),
            ).all()
        }

        receivables = {
            row[0]
            for row in db.query(
                BankReconciliation.accounts_receivable_id
            ).filter(
                BankReconciliation.tenant_id == tenant_id,
                BankReconciliation.accounts_receivable_id.isnot(None),
            ).all()
        }

        return payables, receivables

    @staticmethod
    def _get_client(db, current_user, client_id):

        client = (
            db.query(Client)
            .filter(
                Client.id == client_id,
                Client.tenant_id == current_user.tenant_id,
            )
            .first()
        )

        if not client:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        return client

    @staticmethod
    def _pendentes(db, current_user, client_id, transaction_ids=None):

        query = (
            db.query(BankTransaction)
            .filter(
                BankTransaction.tenant_id == current_user.tenant_id,
                BankTransaction.client_id == client_id,
                BankTransaction.conciliado == False,  # noqa: E712
                BankTransaction.processado == False,  # noqa: E712
                BankTransaction.ignorada == False,  # noqa: E712
            )
        )

        if transaction_ids is not None:
            query = query.filter(
                BankTransaction.id.in_(transaction_ids)
            )

        return query.order_by(
            BankTransaction.data_transacao.desc(),
            BankTransaction.id,
        ).all()

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    @staticmethod
    def listar(db, current_user, client_id):
        """Sugestões já geradas para as transações ainda pendentes do
        cliente. Um lançamento sugerido que entretanto foi vinculado a
        outra transação deixa de ser oferecido."""

        habilitado = AIClient.habilitado()

        # IA desligada (sem ANTHROPIC_API_KEY): não consulta nada — a
        # tela esconde o botão e segue só com a heurística. Assim o
        # sistema funciona mesmo antes de ativar a IA.
        if not habilitado or not client_id:
            return {"habilitado": habilitado, "sugestoes": []}

        AIReconciliationService._get_client(db, current_user, client_id)

        pendentes_ids = [
            t.id
            for t in AIReconciliationService._pendentes(
                db, current_user, client_id
            )
        ]

        if not pendentes_ids:
            return {"habilitado": habilitado, "sugestoes": []}

        registros = (
            db.query(AIReconciliationSuggestion)
            .filter(
                AIReconciliationSuggestion.tenant_id
                == current_user.tenant_id,
                AIReconciliationSuggestion.client_id == client_id,
                AIReconciliationSuggestion.bank_transaction_id.in_(
                    pendentes_ids
                ),
            )
            .all()
        )

        payables_vinc, receivables_vinc = (
            AIReconciliationService._ids_vinculados(
                db, current_user.tenant_id
            )
        )

        payable_ids = [
            r.match_id for r in registros
            if r.tipo_match == "PAYABLE" and r.match_id
        ]

        receivable_ids = [
            r.match_id for r in registros
            if r.tipo_match == "RECEIVABLE" and r.match_id
        ]

        lancamentos = {}

        for Model, ids in (
            (AccountsPayable, payable_ids),
            (AccountsReceivable, receivable_ids),
        ):
            if not ids:
                continue

            for item in (
                db.query(Model)
                .filter(
                    Model.tenant_id == current_user.tenant_id,
                    Model.client_id == client_id,
                    Model.id.in_(ids),
                )
                .all()
            ):
                lancamentos[item.id] = item

        sugestoes = []

        for r in registros:

            match = None

            if r.match_id and r.match_id in lancamentos:

                vinculado = (
                    r.match_id in payables_vinc
                    if r.tipo_match == "PAYABLE"
                    else r.match_id in receivables_vinc
                )

                if not vinculado:

                    item = lancamentos[r.match_id]

                    match = {
                        "tipo": r.tipo_match,
                        "id": item.id,
                        "descricao": item.descricao,
                        "valor": item.valor,
                        "vencimento": item.vencimento,
                    }

            sugestoes.append({
                "transaction_id": r.bank_transaction_id,
                "match": match,
                "financial_contact_id": r.financial_contact_id,
                "novo_fornecedor_nome": r.novo_fornecedor_nome,
                "category_id": r.category_id,
                "subcategory_id": r.subcategory_id,
                "competencia": r.competencia,
                "confianca": r.confianca,
                "justificativa": r.justificativa,
                "created_at": r.created_at,
            })

        return {"habilitado": habilitado, "sugestoes": sugestoes}

    # ------------------------------------------------------------------
    # Geração
    # ------------------------------------------------------------------

    @staticmethod
    def gerar(
        db,
        current_user,
        client_id,
        transaction_ids=None,
        forcar=False
    ):

        if not AIClient.habilitado():
            raise HTTPException(
                status_code=503,
                detail=(
                    "IA não configurada no servidor "
                    "(ANTHROPIC_API_KEY)"
                )
            )

        client = AIReconciliationService._get_client(
            db, current_user, client_id
        )

        pendentes = AIReconciliationService._pendentes(
            db, current_user, client.id, transaction_ids
        )

        if not forcar and pendentes:

            ja_sugeridas = {
                row[0]
                for row in db.query(
                    AIReconciliationSuggestion.bank_transaction_id
                ).filter(
                    AIReconciliationSuggestion.tenant_id
                    == current_user.tenant_id,
                    AIReconciliationSuggestion.bank_transaction_id.in_(
                        [t.id for t in pendentes]
                    ),
                ).all()
            }

            pendentes = [
                t for t in pendentes if t.id not in ja_sugeridas
            ]

        lote = pendentes[: AIReconciliationService.LOTE_MAXIMO]

        restantes = max(
            0,
            len(pendentes) - AIReconciliationService.LOTE_MAXIMO
        )

        if lote:
            AIReconciliationService._processar_lote(
                db, current_user, client, lote
            )

        return {
            "processadas": len(lote),
            "restantes": restantes,
            "sugestoes": AIReconciliationService.listar(
                db, current_user, client.id
            )["sugestoes"],
        }

    @staticmethod
    def descartar(db, current_user, transaction_id):
        """"Não é esse" numa sugestão da IA: apaga a sugestão (ela não
        volta ao recarregar a tela; dá pra pedir de novo com o botão)."""

        (
            db.query(AIReconciliationSuggestion)
            .filter(
                AIReconciliationSuggestion.tenant_id
                == current_user.tenant_id,
                AIReconciliationSuggestion.bank_transaction_id
                == transaction_id,
            )
            .delete(synchronize_session=False)
        )

        db.commit()

        return {"message": "Sugestão descartada"}

    # ------------------------------------------------------------------
    # Montagem do contexto + chamada
    # ------------------------------------------------------------------

    @staticmethod
    def _montar_contexto(db, current_user, client, lote):
        """Monta o texto enviado à IA e os mapas ref -> objeto usados pra
        traduzir a resposta de volta. Tudo filtrado por tenant+cliente."""

        tenant_id = current_user.tenant_id

        S = AIReconciliationService
        limpar = S._limpar_texto

        # ---------------- fornecedores ----------------
        contatos = (
            db.query(FinancialContact)
            .filter(
                FinancialContact.tenant_id == tenant_id,
                FinancialContact.client_id == client.id,
                FinancialContact.ativo == True,  # noqa: E712
            )
            .order_by(FinancialContact.nome)
            .limit(S.CONTATOS_MAXIMO)
            .all()
        )

        mapa_contatos = {}
        ref_por_contato = {}

        for i, contato in enumerate(contatos, start=1):
            ref = f"F{i}"
            mapa_contatos[ref] = contato
            ref_por_contato[contato.id] = ref

        # ---------------- categorias ----------------
        categorias = (
            db.query(ExpenseCategory)
            .filter(
                ExpenseCategory.tenant_id == tenant_id,
                ExpenseCategory.client_id == client.id,
                ExpenseCategory.ativo == True,  # noqa: E712
            )
            .order_by(ExpenseCategory.nome)
            .all()
        )

        categoria_ids = [c.id for c in categorias]

        subcategorias = (
            db.query(ExpenseSubcategory)
            .filter(
                ExpenseSubcategory.category_id.in_(categoria_ids),
                ExpenseSubcategory.ativo == True,  # noqa: E712
            )
            .order_by(ExpenseSubcategory.nome)
            .all()
            if categoria_ids
            else []
        )

        mapa_categorias = {}
        ref_por_categoria = {}
        mapa_subcategorias = {}
        ref_por_subcategoria = {}

        for i, cat in enumerate(categorias, start=1):
            ref = f"C{i}"
            mapa_categorias[ref] = cat
            ref_por_categoria[cat.id] = ref

        for i, sub in enumerate(subcategorias, start=1):
            ref = f"S{i}"
            mapa_subcategorias[ref] = sub
            ref_por_subcategoria[sub.id] = ref

        # ---------------- lançamentos candidatos ----------------
        payables_vinc, receivables_vinc = S._ids_vinculados(db, tenant_id)

        datas = [t.data_transacao for t in lote]

        data_min = min(datas) - timedelta(days=S.JANELA_DIAS_CANDIDATOS)
        data_max = max(datas) + timedelta(days=S.JANELA_DIAS_CANDIDATOS)

        tipos_no_lote = {t.tipo for t in lote}

        # Contas a pagar geradas pela folha (uma por funcionário) nunca são
        # candidatas a vincular a outra transação.
        ids_folha = {
            row[0]
            for row in db.query(PayrollItem.accounts_payable_id)
            .filter(PayrollItem.accounts_payable_id.isnot(None))
            .all()
        }

        mapa_lancamentos = {}
        linhas_lancamentos = []

        fontes = []

        if any(t != "CREDITO" for t in tipos_no_lote):
            fontes.append(
                (AccountsPayable, "PAYABLE", "A PAGAR",
                 payables_vinc | ids_folha)
            )

        if "CREDITO" in tipos_no_lote:
            fontes.append(
                (AccountsReceivable, "RECEIVABLE", "A RECEBER",
                 receivables_vinc)
            )

        contador = 0

        for Model, tipo, rotulo, excluir in fontes:

            itens = (
                db.query(Model)
                .filter(
                    Model.tenant_id == tenant_id,
                    Model.client_id == client.id,
                    Model.vencimento >= data_min,
                    Model.vencimento <= data_max,
                )
                .order_by(Model.vencimento.desc())
                .limit(S.CANDIDATOS_MAXIMO * 2)
                .all()
            )

            itens = [i for i in itens if i.id not in excluir][
                : S.CANDIDATOS_MAXIMO
            ]

            for item in itens:
                contador += 1
                ref = f"L{contador}"
                mapa_lancamentos[ref] = (item, tipo)

                linhas_lancamentos.append(
                    " | ".join([
                        ref,
                        rotulo,
                        str(item.vencimento),
                        f"{Decimal(str(item.valor)):.2f}",
                        limpar(S.mascarar_documentos(item.descricao)),
                        ref_por_contato.get(
                            item.financial_contact_id, "-"
                        ),
                        ref_por_categoria.get(item.category_id, "-"),
                        ref_por_subcategoria.get(
                            item.subcategory_id, "-"
                        ),
                    ])
                )

        # ---------------- histórico (exemplos) ----------------
        linhas_historico = []

        for Model, coluna, rotulo in (
            (AccountsPayable,
             BankReconciliation.accounts_payable_id, "DEBITO"),
            (AccountsReceivable,
             BankReconciliation.accounts_receivable_id, "CREDITO"),
        ):
            rows = (
                db.query(
                    BankTransaction.descricao,
                    Model.financial_contact_id,
                    Model.category_id,
                    Model.subcategory_id,
                    Model.competencia,
                    BankTransaction.data_transacao,
                )
                .select_from(BankReconciliation)
                .join(
                    BankTransaction,
                    BankTransaction.id
                    == BankReconciliation.bank_transaction_id,
                )
                .join(Model, Model.id == coluna)
                .filter(
                    BankReconciliation.tenant_id == tenant_id,
                    BankTransaction.client_id == client.id,
                )
                .order_by(BankReconciliation.data_conciliacao.desc())
                .limit(S.HISTORICO_EXEMPLOS // 2)
                .all()
            )

            for (
                descricao, contato_id, cat_id, sub_id, comp, data
            ) in rows:
                linhas_historico.append(
                    f"{rotulo} {data} \"{limpar(S.mascarar_documentos(descricao))}\""
                    f" -> {ref_por_contato.get(contato_id, '?')}"
                    f" / {ref_por_categoria.get(cat_id, '?')}"
                    f" / {ref_por_subcategoria.get(sub_id, '-')}"
                    f" / comp {comp or '-'}"
                )

        # ---------------- transações do lote ----------------
        mapa_transacoes = {}
        linhas_transacoes = []

        for i, t in enumerate(lote, start=1):
            ref = f"T{i}"
            mapa_transacoes[ref] = t
            linhas_transacoes.append(
                " | ".join([
                    ref,
                    str(t.data_transacao),
                    t.tipo,
                    f"{Decimal(str(t.valor)):.2f}",
                    limpar(
                        S.mascarar_documentos(t.descricao),
                        200
                    ),
                ])
            )

        # ---------------- texto ----------------
        nome_cliente = limpar(
            client.nome_fantasia or client.razao_social
        )

        partes = [
            f"CLIENTE DO ESCRITÓRIO: {nome_cliente}",
            "",
            "FORNECEDORES/CLIENTES CADASTRADOS (ref | nome | tipo):",
        ]

        partes += [
            f"{ref} | {limpar(c.nome)} | {c.tipo or '-'}"
            for ref, c in mapa_contatos.items()
        ] or ["(nenhum)"]

        partes += ["", "CATEGORIAS (ref | nome) e suas SUBCATEGORIAS:"]

        subs_por_cat = {}
        for ref, sub in mapa_subcategorias.items():
            subs_por_cat.setdefault(sub.category_id, []).append(
                f"  {ref} | {limpar(sub.nome)}"
            )

        if mapa_categorias:
            for ref, cat in mapa_categorias.items():
                partes.append(f"{ref} | {limpar(cat.nome)}")
                partes += subs_por_cat.get(cat.id, [])
        else:
            partes.append("(nenhuma)")

        partes += [
            "",
            "LANÇAMENTOS EM ABERTO QUE PODEM SER VINCULADOS "
            "(ref | tipo | vencimento | valor | descrição | fornecedor | "
            "categoria | subcategoria):",
        ]
        partes += linhas_lancamentos or ["(nenhum)"]

        partes += [
            "",
            "HISTÓRICO DE CONCILIAÇÕES DESTE CLIENTE "
            "(tipo data \"descrição no extrato\" -> fornecedor / "
            "categoria / subcategoria / competência):",
        ]
        partes += linhas_historico or ["(sem histórico ainda)"]

        partes += [
            "",
            "TRANSAÇÕES A CONCILIAR (ref | data | tipo | valor | "
            "descrição no extrato):",
        ]
        partes += linhas_transacoes

        return {
            "texto": "\n".join(partes),
            "transacoes": mapa_transacoes,
            "contatos": mapa_contatos,
            "categorias": mapa_categorias,
            "subcategorias": mapa_subcategorias,
            "lancamentos": mapa_lancamentos,
        }

    @staticmethod
    def interpretar_resposta(resposta, contexto):
        """Traduz a resposta da IA (refs) em valores reais, validando
        tudo. Devolve {transaction_id: dict_de_campos}. Função pura (sem
        banco) pra poder ser testada isoladamente."""

        S = AIReconciliationService

        resultados = {}
        lancamentos_usados = set()

        nomes_contatos = {
            (c.nome or "").strip().lower(): c
            for c in contexto["contatos"].values()
        }

        for item in (resposta or {}).get("sugestoes") or []:

            if not isinstance(item, dict):
                continue

            def ref(campo):
                valor = item.get(campo)
                return valor.strip().upper() if isinstance(valor, str) else None

            transacao = contexto["transacoes"].get(ref("transacao"))

            if transacao is None or transacao.id in resultados:
                continue

            campos = {
                "tipo_match": None,
                "match_id": None,
                "financial_contact_id": None,
                "novo_fornecedor_nome": None,
                "category_id": None,
                "subcategory_id": None,
                "competencia": None,
                "confianca": (
                    item.get("confianca")
                    if item.get("confianca") in S.CONFIANCAS
                    else "BAIXA"
                ),
                "justificativa": S._limpar_texto(
                    S.mascarar_documentos(item.get("justificativa")),
                    300
                ) or None,
            }

            # ---- lançamento pra vincular ----
            lanc_ref = ref("lancamento")
            candidato = contexto["lancamentos"].get(lanc_ref)

            if candidato and lanc_ref not in lancamentos_usados:

                lancamento, tipo = candidato

                tipo_ok = (
                    (tipo == "RECEIVABLE")
                    == (transacao.tipo == "CREDITO")
                )

                diferenca = abs(
                    Decimal(str(lancamento.valor))
                    - Decimal(str(transacao.valor))
                )

                valor_ok = (
                    BankReconciliationService._dentro_tolerancia_valor(
                        diferenca,
                        lancamento.valor
                    )
                )

                if tipo_ok and valor_ok:
                    lancamentos_usados.add(lanc_ref)
                    campos["tipo_match"] = tipo
                    campos["match_id"] = lancamento.id
                    campos["financial_contact_id"] = (
                        lancamento.financial_contact_id
                    )
                    campos["category_id"] = lancamento.category_id
                    campos["subcategory_id"] = lancamento.subcategory_id
                    campos["competencia"] = lancamento.competencia

            if not campos["match_id"]:

                # ---- fornecedor ----
                contato = contexto["contatos"].get(ref("fornecedor"))

                if contato:
                    campos["financial_contact_id"] = contato.id

                else:
                    nome_novo = S._limpar_texto(
                        S.mascarar_documentos(
                            item.get("novo_fornecedor_nome")
                        ),
                        120
                    )

                    # Remove marcadores de documento que sobraram.
                    nome_novo = re.sub(
                        r"\[(CPF|CNPJ)\]", "", nome_novo
                    ).strip(" -")

                    existente = nomes_contatos.get(nome_novo.lower())

                    if existente:
                        campos["financial_contact_id"] = existente.id
                    elif len(nome_novo) >= 2:
                        campos["novo_fornecedor_nome"] = nome_novo

                # ---- categoria / subcategoria ----
                categoria = contexto["categorias"].get(ref("categoria"))
                subcategoria = contexto["subcategorias"].get(
                    ref("subcategoria")
                )

                if subcategoria and categoria is None:
                    categoria = next(
                        (
                            c for c in contexto["categorias"].values()
                            if c.id == subcategoria.category_id
                        ),
                        None
                    )

                if categoria:
                    campos["category_id"] = categoria.id

                    if (
                        subcategoria
                        and subcategoria.category_id == categoria.id
                    ):
                        campos["subcategory_id"] = subcategoria.id

                campos["competencia"] = (
                    PayrollPDFService.normalizar_competencia(
                        item.get("competencia")
                    )
                )

            resultados[transacao.id] = campos

        return resultados

    @staticmethod
    def _processar_lote(db, current_user, client, lote):

        contexto = AIReconciliationService._montar_contexto(
            db, current_user, client, lote
        )

        try:
            resposta = AIClient.chamar_ferramenta(
                model=settings.AI_MODEL_CONCILIACAO,
                system=_SYSTEM_PROMPT,
                content=[{"type": "text", "text": contexto["texto"]}],
                tool=_TOOL,
                max_tokens=8000,
            )
        except AIError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "A IA não respondeu agora — tente de novo "
                    "em instantes"
                )
            ) from exc

        resultados = AIReconciliationService.interpretar_resposta(
            resposta,
            contexto
        )

        ids_lote = [t.id for t in lote]

        (
            db.query(AIReconciliationSuggestion)
            .filter(
                AIReconciliationSuggestion.tenant_id
                == current_user.tenant_id,
                AIReconciliationSuggestion.bank_transaction_id.in_(
                    ids_lote
                ),
            )
            .delete(synchronize_session=False)
        )

        for transacao in lote:

            campos = resultados.get(transacao.id)

            # A IA pulou essa transação: grava uma sugestão "vazia" pra
            # não ficar pedindo de novo em loop (o botão "Refazer" força).
            if campos is None:
                campos = {
                    "confianca": "BAIXA",
                    "justificativa": (
                        "A IA não conseguiu sugerir nada para esta "
                        "transação."
                    ),
                }

            db.add(
                AIReconciliationSuggestion(
                    tenant_id=current_user.tenant_id,
                    client_id=client.id,
                    bank_transaction_id=transacao.id,
                    modelo=settings.AI_MODEL_CONCILIACAO,
                    **campos,
                )
            )

        db.commit()
