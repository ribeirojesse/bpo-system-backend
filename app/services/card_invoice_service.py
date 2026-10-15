"""Conciliação de fatura de cartão de crédito.

Mesma mecânica da folha de pagamento (app/services/payroll_service.py):
o pagamento da fatura que saiu no extrato é conferido contra a soma dos
itens lidos da fatura e, fechando, cada item vira um lançamento em
contas a pagar — todos com a categoria FATURA CARTAO do cliente e a
mesma competência, informada à mão na tela.

Diferenças em relação à folha:
  - a categoria não é escolhida: é sempre a FATURA CARTAO do cliente,
    criada na hora se ainda não existir;
  - cada item pode ter a sua própria subcategoria (dessa categoria);
  - item com valor negativo (estorno, crédito, pagamento da fatura
    anterior) é gravado como negativo, pra soma fechar com o extrato e
    pro DRE descontar de verdade.
"""

import re

from decimal import Decimal

from fastapi import HTTPException

from app.models.accounts_payable import AccountsPayable
from app.models.bank_account import BankAccount
from app.models.card_invoice_batch import CardInvoiceBatch
from app.models.card_invoice_item import CardInvoiceItem
from app.models.expense_category import ExpenseCategory
from app.models.expense_subcategory import ExpenseSubcategory
from app.models.financial_contact import FinancialContact

from app.services import card_invoice_parser

from app.services.card_invoice_pdf_service import (
    CardInvoiceExtractionError,
    CardInvoicePDFService
)


# Nome fixo da categoria e do fornecedor usados nos lançamentos.
NOME_CATEGORIA = "FATURA CARTAO"

NOME_CONTATO = "FATURA CARTAO"


class CardInvoiceService:

    # Mesma folga da folha: centavos de arredondamento passam, o resto
    # trava até a pessoa ajustar os itens na tela.
    TOLERANCIA = Decimal("1.00")

    # ==================================================================
    # Validações
    # ==================================================================

    @staticmethod
    def _validar_transacao(db, transaction):

        if transaction.tipo != "DEBITO":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Fatura de cartão só pode ser processada em "
                    "débitos (o pagamento da fatura)"
                )
            )

        if transaction.conciliado or transaction.processado:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa transação já foi conciliada ou processada"
                )
            )

        batch_existente = (
            db.query(CardInvoiceBatch)
            .filter(
                CardInvoiceBatch.bank_transaction_id
                == transaction.id
            )
            .first()
        )

        if batch_existente:

            raise HTTPException(
                status_code=400,
                detail="Essa fatura já foi processada"
            )

    @staticmethod
    def _extrair(
        conteudo,
        media_type,
        valor_esperado=None,
        referencia=None
    ):

        try:
            return CardInvoicePDFService.extrair(
                conteudo,
                media_type,
                valor_esperado,
                referencia
            )
        except CardInvoiceExtractionError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc)
            ) from exc

    # ==================================================================
    # Conferência: a fatura é mesmo a do cartão desta transação?
    # ==================================================================

    @staticmethod
    def conferir_cartao(db, current_user, transaction, identificacao):
        """Compara o que a fatura diz (banco emissor e finais de
        cartão/conta) com o que se sabe da transação do extrato: a
        descrição do lançamento e a conta bancária em que ele caiu.

        Devolve {"status", "detalhe", ...} com status:
          CONFERE    bateu o final do cartão ou o nome do banco;
          DIVERGE    os dois lados identificam cartões/bancos
                     diferentes — é o caso de pôr a fatura do Itaú num
                     pagamento do Bradesco;
          SEM_DADOS  não há o que comparar (fatura escaneada, descrição
                     genérica como "PAGAMENTO FATURA").

        DIVERGE não impede de gravar à força: pagar a fatura de um cartão
        usando a conta de outro banco é legítimo. Mas aí a tela pede
        confirmação explícita antes (ver `processar`)."""

        banco_fatura = (identificacao or {}).get("banco")

        finais_fatura = set(
            (identificacao or {}).get("finais") or []
        )

        conta = None

        if transaction.bank_account_id:

            conta = (
                db.query(BankAccount)
                .filter(
                    BankAccount.id == transaction.bank_account_id,
                    BankAccount.tenant_id == current_user.tenant_id,
                )
                .first()
            )

        partes = [transaction.descricao or ""]

        if conta:
            partes.extend([
                conta.banco or "",
                conta.conta or "",
            ])

        texto_transacao = " ".join(partes)

        finais_transacao = card_invoice_parser.finais_no_texto(
            texto_transacao
        )

        # Final de conta sem máscara ("97889-7" → "8897").
        digitos_conta = re.sub(r"\D", "", (conta.conta if conta else ""))

        if len(digitos_conta) >= 4:
            finais_transacao.add(digitos_conta[-4:])

        banco_transacao = card_invoice_parser.banco_no_texto(
            texto_transacao
        )

        base = {
            "banco_fatura": banco_fatura,
            "banco_transacao": banco_transacao,
            "finais_fatura": sorted(finais_fatura),
            "finais_transacao": sorted(finais_transacao),
        }

        comuns = finais_fatura & finais_transacao

        if comuns:
            return {
                **base,
                "status": "CONFERE",
                "detalhe": (
                    f"Final {sorted(comuns)[0]} confere com a "
                    "transação."
                ),
            }

        if (
            banco_fatura
            and banco_transacao
            and banco_fatura == banco_transacao
        ):
            return {
                **base,
                "status": "CONFERE",
                "detalhe": f"Banco {banco_fatura} confere.",
            }

        if (
            banco_fatura
            and banco_transacao
            and banco_fatura != banco_transacao
        ):
            return {
                **base,
                "status": "DIVERGE",
                "detalhe": (
                    f"A fatura é do {banco_fatura}, mas o pagamento "
                    f"está em conta/descrição do {banco_transacao}."
                ),
            }

        if finais_fatura and finais_transacao:
            return {
                **base,
                "status": "DIVERGE",
                "detalhe": (
                    "A fatura é do cartão final "
                    f"{', '.join(sorted(finais_fatura))}, e a transação "
                    f"aponta final {', '.join(sorted(finais_transacao))}."
                ),
            }

        return {
            **base,
            "status": "SEM_DADOS",
            "detalhe": (
                "Não foi possível confirmar pelo documento de qual "
                "cartão é esta fatura — confira antes de gravar."
            ),
        }

    # ==================================================================
    # Categoria / fornecedor fixos
    # ==================================================================

    @staticmethod
    def categoria_fatura(db, current_user, client_id):
        """Categoria FATURA CARTAO do cliente. Procura sem diferenciar
        maiúscula/acento e cria se não existir — assim o cliente novo
        não precisa de cadastro manual antes da primeira fatura."""

        categorias = (
            db.query(ExpenseCategory)
            .filter(
                ExpenseCategory.tenant_id == current_user.tenant_id,
                ExpenseCategory.client_id == client_id,
            )
            .all()
        )

        def normalizar(texto):

            import unicodedata

            texto = unicodedata.normalize("NFKD", texto or "")

            texto = "".join(
                c for c in texto
                if not unicodedata.combining(c)
            )

            return " ".join(texto.upper().split())

        alvo = normalizar(NOME_CATEGORIA)

        for categoria in categorias:

            if normalizar(categoria.nome) == alvo:
                return categoria

        categoria = ExpenseCategory(
            tenant_id=current_user.tenant_id,
            client_id=client_id,
            nome=NOME_CATEGORIA,
            ativo=True
        )

        db.add(categoria)

        db.flush()

        return categoria

    @staticmethod
    def _contato_fatura(db, current_user, client_id):

        contato = (
            db.query(FinancialContact)
            .filter(
                FinancialContact.tenant_id == current_user.tenant_id,
                FinancialContact.client_id == client_id,
                FinancialContact.nome == NOME_CONTATO,
            )
            .first()
        )

        if contato:
            return contato

        contato = FinancialContact(
            tenant_id=current_user.tenant_id,
            client_id=client_id,
            nome=NOME_CONTATO,
            tipo="FORNECEDOR",
            ativo=True
        )

        db.add(contato)

        db.flush()

        return contato

    @staticmethod
    def _subcategorias_validas(db, category_id):

        return {
            row[0]
            for row in (
                db.query(ExpenseSubcategory.id)
                .filter(
                    ExpenseSubcategory.category_id == category_id
                )
                .all()
            )
        }

    # ==================================================================
    # Pré-visualização
    # ==================================================================

    @staticmethod
    def pre_visualizar(
        db,
        current_user,
        transaction,
        conteudo,
        media_type
    ):
        """Lê a fatura e devolve os itens pra conferência na tela, SEM
        gravar nada. A tela edita a lista, escolhe a subcategoria de cada
        item e a competência, e só então chama `processar`."""

        CardInvoiceService._validar_transacao(db, transaction)

        extracao = CardInvoiceService._extrair(
            conteudo,
            media_type,
            transaction.valor,
            transaction.data_transacao
        )

        valor_total = CardInvoicePDFService._soma(extracao["itens"])

        valor_transacao = Decimal(str(transaction.valor))

        diferenca = valor_transacao - valor_total

        avisos = list(extracao["avisos"])

        # Conferência do cartão: lida sempre do próprio arquivo, mesmo
        # quando os itens vieram da IA (é leitura local e barata).
        identificacao = CardInvoicePDFService.identificar(
            conteudo,
            media_type
        )

        identificacao["banco"] = (
            identificacao.get("banco") or extracao["banco"]
        )

        conferencia = CardInvoiceService.conferir_cartao(
            db,
            current_user,
            transaction,
            identificacao
        )

        if conferencia["status"] == "DIVERGE":
            avisos.insert(
                0,
                f"Confira o cartão: {conferencia['detalhe']} "
                "Se o pagamento for mesmo desta fatura (cartão de um "
                "banco pago pela conta de outro), confirme na opção "
                "abaixo antes de gravar."
            )

        total_documento = extracao["total_documento"]

        # Caso clássico de transação errada: a leitura fecha com o total
        # impresso na fatura, mas não com o débito escolhido no extrato.
        if (
            total_documento is not None
            and abs(valor_total - total_documento) <= Decimal("0.01")
            and abs(diferenca) > CardInvoiceService.TOLERANCIA
        ):
            avisos.insert(
                0,
                "Os itens fecham com o total impresso na fatura "
                f"(R$ {total_documento:.2f}), mas o pagamento "
                f"selecionado no extrato é de R$ {valor_transacao:.2f}. "
                "Confira se essa é a transação do pagamento desta "
                "fatura — ou se houve pagamento parcial/parcelamento."
            )

        categoria = CardInvoiceService.categoria_fatura(
            db,
            current_user,
            transaction.client_id
        )

        # A categoria pode ter sido criada agora: sem o commit ela não
        # existiria pro front listar as subcategorias.
        db.commit()

        return {
            "metodo": extracao["metodo"],
            "itens": [
                {
                    "data": (
                        item["data"].isoformat()
                        if item["data"]
                        else None
                    ),
                    "descricao": item["descricao"],
                    "valor": float(item["valor"]),
                    "parcela": item["parcela"],
                    "cartao": item["cartao"],
                    "subcategory_id": None,
                }
                for item in extracao["itens"]
            ],
            "valor_total": float(valor_total),
            "valor_transacao": float(valor_transacao),
            "diferenca": float(abs(diferenca)),
            "dentro_tolerancia": (
                abs(diferenca) <= CardInvoiceService.TOLERANCIA
            ),
            "total_documento": (
                float(extracao["total_documento"])
                if extracao["total_documento"] is not None
                else None
            ),
            "vencimento": (
                extracao["vencimento"].isoformat()
                if extracao["vencimento"]
                else None
            ),
            "banco": extracao["banco"],
            "avisos": avisos,
            "category_id": str(categoria.id),
            "category_nome": categoria.nome,
            "conferencia": conferencia,
        }

    # ==================================================================
    # Gravação
    # ==================================================================

    @staticmethod
    def processar(
        db,
        current_user,
        transaction,
        conteudo,
        media_type,
        competencia,
        itens_confirmados=None,
        confirmar_divergencia=False
    ):
        """Grava a fatura: um lançamento por item, todos na categoria
        FATURA CARTAO e na mesma competência. Usa a lista conferida na
        tela quando ela vem; senão lê o arquivo de novo.

        Antes de gravar, confere se a fatura é mesmo do cartão daquela
        transação (banco emissor e final do cartão). Divergência só passa
        com `confirmar_divergencia` — é o que evita gravar a fatura do
        Itaú no pagamento do cartão do Bradesco por engano."""

        CardInvoiceService._validar_transacao(db, transaction)

        identificacao = CardInvoicePDFService.identificar(
            conteudo,
            media_type
        )

        conferencia = CardInvoiceService.conferir_cartao(
            db,
            current_user,
            transaction,
            identificacao
        )

        if (
            conferencia["status"] == "DIVERGE"
            and not confirmar_divergencia
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "Esta fatura parece não ser do cartão desta "
                        "transação"
                    ),
                    "detalhe": conferencia["detalhe"],
                    "requer_confirmacao": True,
                    "conferencia": conferencia,
                }
            )

        competencia = (competencia or "").strip()

        if not CardInvoicePDFService.normalizar_competencia(
            competencia
        ):
            raise HTTPException(
                status_code=400,
                detail="Informe a competência no formato MM/AAAA"
            )

        # ==========================================
        # ITENS
        # ==========================================

        extracao = None

        if itens_confirmados is not None:

            itens, _avisos = CardInvoicePDFService.limpar_itens(
                itens_confirmados,
                transaction.data_transacao
            )

            subcategoria_por_indice = [
                (item or {}).get("subcategory_id")
                for item in itens_confirmados
                if isinstance(item, dict)
            ]

        else:

            extracao = CardInvoiceService._extrair(
                conteudo,
                media_type,
                transaction.valor,
                transaction.data_transacao
            )

            itens = extracao["itens"]

            subcategoria_por_indice = [None] * len(itens)

        if not itens:

            raise HTTPException(
                status_code=400,
                detail="Nenhum lançamento encontrado na fatura"
            )

        # ==========================================
        # CONFERE COM O EXTRATO
        # ==========================================

        valor_total = CardInvoicePDFService._soma(itens)

        valor_transacao = Decimal(str(transaction.valor))

        diferenca = abs(valor_transacao - valor_total)

        if diferenca > CardInvoiceService.TOLERANCIA:

            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "A soma dos itens da fatura está diferente do "
                        "valor pago no extrato"
                    ),
                    "valor_fatura": float(valor_total),
                    "valor_ofx": float(valor_transacao),
                    "diferenca": float(diferenca),
                }
            )

        # ==========================================
        # CATEGORIA, SUBCATEGORIAS E FORNECEDOR
        # ==========================================

        categoria = CardInvoiceService.categoria_fatura(
            db,
            current_user,
            transaction.client_id
        )

        validas = CardInvoiceService._subcategorias_validas(
            db,
            categoria.id
        )

        subcategorias = []

        for posicao in range(len(itens)):

            bruto = (
                subcategoria_por_indice[posicao]
                if posicao < len(subcategoria_por_indice)
                else None
            )

            bruto = (str(bruto).strip() if bruto else "") or None

            if bruto is None:
                subcategorias.append(None)
                continue

            encontrada = next(
                (
                    valida for valida in validas
                    if str(valida) == bruto
                ),
                None
            )

            if encontrada is None:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Subcategoria inválida em um dos itens — use "
                        f"uma subcategoria da categoria "
                        f"{categoria.nome}"
                    )
                )

            subcategorias.append(encontrada)

        contato = CardInvoiceService._contato_fatura(
            db,
            current_user,
            transaction.client_id
        )

        # ==========================================
        # LOTE DA FATURA
        # ==========================================

        batch = CardInvoiceBatch(
            tenant_id=current_user.tenant_id,
            client_id=transaction.client_id,
            bank_transaction_id=transaction.id,
            category_id=categoria.id,
            competencia=competencia,
            valor_total=valor_total,
            valor_transacao=valor_transacao,
            valor_total_documento=(
                extracao["total_documento"] if extracao else None
            ),
            vencimento=(
                extracao["vencimento"] if extracao else None
            ),
            banco=(
                extracao["banco"] if extracao else None
            ),
            conciliado=True,
            processado=True
        )

        db.add(batch)

        db.flush()

        # ==========================================
        # LANÇAMENTOS
        # ==========================================

        for posicao, item in enumerate(itens):

            descricao = item["descricao"]

            if item["parcela"]:
                descricao = f"{descricao} ({item['parcela']})"

            observacao_item = "Fatura de cartão"

            if item["cartao"]:
                observacao_item = (
                    f"Fatura de cartão - final {item['cartao']}"
                )

            payable = AccountsPayable(
                tenant_id=current_user.tenant_id,
                client_id=transaction.client_id,
                financial_contact_id=contato.id,
                category_id=categoria.id,
                subcategory_id=subcategorias[posicao],
                descricao=descricao[:200],
                valor=item["valor"],
                vencimento=transaction.data_transacao,
                competencia=competencia,
                status="PAGO",
                data_pagamento=transaction.data_transacao,
                observacao=observacao_item
            )

            db.add(payable)

            db.flush()

            db.add(
                CardInvoiceItem(
                    batch_id=batch.id,
                    data_compra=item["data"],
                    descricao=item["descricao"][:200],
                    valor=item["valor"],
                    parcela=item["parcela"],
                    cartao=item["cartao"],
                    accounts_payable_id=payable.id
                )
            )

        # ==========================================
        # MARCA A TRANSAÇÃO
        # ==========================================

        transaction.processado = True

        transaction.conciliado = True

        db.commit()

        return {
            "message": "Fatura conciliada com sucesso",
            "itens": len(itens),
            "valor_total": float(valor_total),
            "valor_transacao": float(valor_transacao),
            "diferenca": float(diferenca),
            "competencia": competencia,
            "categoria": categoria.nome,
            "conferencia": conferencia["status"],
            "conciliado": True,
        }
