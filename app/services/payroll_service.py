from decimal import Decimal

from fastapi import HTTPException

from app.models.payroll_batch import PayrollBatch
from app.models.payroll_item import PayrollItem
from app.models.accounts_payable import AccountsPayable
from app.models.financial_contact import FinancialContact

from app.repositories.expense_category_repository import (
    ExpenseCategoryRepository
)

from app.services.payroll_pdf_service import (
    PayrollExtractionError,
    PayrollPDFService
)


class PayrollService:

    TOLERANCIA = Decimal("1.00")

    @staticmethod
    def _validar_transacao(db, transaction):

        if transaction.tipo != "DEBITO":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Folha só pode ser "
                    "processada em débitos"
                )
            )

        if transaction.conciliado or transaction.processado:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa transação já foi conciliada "
                    "ou processada"
                )
            )

        batch_existente = (
            db.query(PayrollBatch)
            .filter(
                PayrollBatch.bank_transaction_id
                == transaction.id
            )
            .first()
        )

        if batch_existente:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa folha já foi processada"
                )
            )

    @staticmethod
    def _extrair(conteudo, media_type, valor_esperado=None):

        try:
            return PayrollPDFService.extrair(
                conteudo,
                media_type,
                valor_esperado
            )
        except PayrollExtractionError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc)
            ) from exc

    @staticmethod
    def pre_visualizar(
        db,
        current_user,
        transaction,
        conteudo,
        media_type
    ):
        """Lê o comprovante e devolve a lista de funcionários extraída,
        SEM gravar nada — a tela mostra a lista pra conferência/edição e
        só depois chama processar_pdf com a lista confirmada. Assim uma
        leitura errada (layout novo de banco, PDF ruim) nunca vira
        lançamento sem alguém ter olhado antes."""

        PayrollService._validar_transacao(db, transaction)

        extracao = PayrollService._extrair(
            conteudo,
            media_type,
            transaction.valor
        )

        valor_total = sum(
            (f["valor"] for f in extracao["funcionarios"]),
            Decimal("0.00")
        )

        valor_transacao = Decimal(str(transaction.valor))

        diferenca = abs(valor_transacao - valor_total)

        return {
            "metodo": extracao["metodo"],
            "funcionarios": [
                {
                    "funcionario": f["funcionario"],
                    "cpf": f["cpf"],
                    "valor": float(f["valor"]),
                }
                for f in extracao["funcionarios"]
            ],
            "valor_total": float(valor_total),
            "valor_transacao": float(valor_transacao),
            "diferenca": float(diferenca),
            "dentro_tolerancia": (
                diferenca <= PayrollService.TOLERANCIA
            ),
            "valor_total_documento": (
                float(extracao["valor_total_documento"])
                if extracao["valor_total_documento"] is not None
                else None
            ),
            "competencia_detectada": extracao["competencia_detectada"],
            "banco": extracao["banco"],
            "avisos": extracao["avisos"],
        }

    @staticmethod
    def processar_pdf(
        db,
        current_user,
        transaction,
        conteudo,
        media_type,
        competencia,
        category_id,
        funcionarios_confirmados=None
    ):
        """Grava a folha. Se `funcionarios_confirmados` vier (lista
        conferida/editada na tela depois da pré-visualização), usa ela e
        não lê o arquivo de novo; senão, extrai do arquivo (fluxo antigo,
        mantido por compatibilidade)."""

        PayrollService._validar_transacao(db, transaction)

        category = ExpenseCategoryRepository.get_by_id(
            db,
            current_user.tenant_id,
            category_id
        )

        if (
            not category
            or category.client_id != transaction.client_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Categoria inválida para este cliente"
            )

        # ==========================================
        # FUNCIONÁRIOS
        # ==========================================

        if funcionarios_confirmados is not None:

            funcionarios, _avisos = (
                PayrollPDFService.limpar_funcionarios(
                    funcionarios_confirmados
                )
            )

        else:

            funcionarios = PayrollService._extrair(
                conteudo,
                media_type,
                transaction.valor
            )["funcionarios"]

        if not funcionarios:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Nenhum funcionário "
                    "encontrado no PDF"
                )
            )

        # ==========================================
        # TOTAL PDF
        # ==========================================

        valor_total = sum(
            (f["valor"] for f in funcionarios),
            Decimal("0.00")
        )

        valor_transacao = Decimal(
            str(transaction.valor)
        )

        diferenca = abs(
            valor_transacao
            - valor_total
        )

        # ==========================================
        # VALIDA DIFERENÇA
        # ==========================================

        if diferenca > PayrollService.TOLERANCIA:

            raise HTTPException(
                status_code=400,
                detail={
                    "message":
                    "Valor da folha diferente do OFX",

                    "valor_pdf":
                    float(valor_total),

                    "valor_ofx":
                    float(valor_transacao),

                    "diferenca":
                    float(diferenca)
                }
            )

        # ==========================================
        # CONTATO PADRÃO
        # ==========================================

        contato_folha = (
            db.query(FinancialContact)
            .filter(
                FinancialContact.tenant_id
                == current_user.tenant_id,

                FinancialContact.client_id
                == transaction.client_id,

                FinancialContact.nome
                == "FOLHA DE PAGAMENTO"
            )
            .first()
        )

        if not contato_folha:

            contato_folha = FinancialContact(
                tenant_id=current_user.tenant_id,

                client_id=transaction.client_id,

                nome="FOLHA DE PAGAMENTO",

                tipo="FORNECEDOR",

                ativo=True
            )

            db.add(contato_folha)

            db.flush()

        # ==========================================
        # CRIA BATCH
        # ==========================================

        batch = PayrollBatch(
            tenant_id=current_user.tenant_id,

            client_id=transaction.client_id,

            bank_transaction_id=transaction.id,

            competencia=competencia,

            valor_total=valor_total,

            valor_transacao=valor_transacao,

            conciliado=True,

            processado=True
        )

        db.add(batch)

        db.flush()

        # ==========================================
        # CRIA PAYABLES
        # ==========================================

        for funcionario in funcionarios:

            valor_funcionario = funcionario["valor"]

            payable = AccountsPayable(
                tenant_id=current_user.tenant_id,

                client_id=transaction.client_id,

                financial_contact_id=
                contato_folha.id,

                category_id=category_id,

                descricao=(
                    f"Salário - "
                    f"{funcionario['funcionario']}"
                ),

                valor=valor_funcionario,

                vencimento=
                transaction.data_transacao,

                competencia=competencia,

                status="PAGO",

                data_pagamento=
                transaction.data_transacao
            )

            db.add(payable)

            db.flush()

            item = PayrollItem(
                batch_id=batch.id,

                funcionario=
                funcionario["funcionario"],

                cpf=funcionario.get("cpf"),

                valor=valor_funcionario,

                accounts_payable_id=
                payable.id
            )

            db.add(item)

        # ==========================================
        # MARCA TRANSAÇÃO
        # ==========================================

        transaction.processado = True

        transaction.conciliado = True

        db.commit()

        return {
            "message":
            "Folha conciliada com sucesso",

            "funcionarios":
            len(funcionarios),

            "valor_total":
            float(valor_total),

            "valor_transacao":
            float(valor_transacao),

            "diferenca":
            float(diferenca),

            "conciliado":
            True
        }