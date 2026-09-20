from decimal import Decimal

from fastapi import HTTPException

from app.models.payroll_batch import PayrollBatch
from app.models.payroll_item import PayrollItem
from app.models.accounts_payable import AccountsPayable
from app.models.financial_contact import FinancialContact

from app.services.payroll_pdf_service import (
    PayrollPDFService
)


class PayrollService:

    TOLERANCIA = Decimal("1.00")

    @staticmethod
    def processar_pdf(
        db,
        current_user,
        transaction,
        caminho_pdf,
        competencia,
        category_id
    ):

        # ==========================================
        # VALIDA TIPO
        # ==========================================

        if transaction.tipo != "DEBITO":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Folha só pode ser "
                    "processada em débitos"
                )
            )

        # ==========================================
        # BLOQUEIA DUPLICIDADE
        # ==========================================

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

        # ==========================================
        # EXTRAI PDF
        # ==========================================

        texto = (
            PayrollPDFService.extrair_texto(
                caminho_pdf
            )
        )

        funcionarios = (
            PayrollPDFService
            .extrair_funcionarios(
                texto
            )
        )

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

        valor_total = Decimal(
            str(
                sum(
                    f["valor"]
                    for f in funcionarios
                )
            )
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

            valor_funcionario = Decimal(
                str(funcionario["valor"])
            )

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