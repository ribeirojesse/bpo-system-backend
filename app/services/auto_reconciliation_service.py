from datetime import timedelta

from app.models.accounts_payable import (
    AccountsPayable
)

from app.models.accounts_receivable import (
    AccountsReceivable
)

from app.models.bank_reconciliation import (
    BankReconciliation
)


class AutoReconciliationService:

    TOLERANCIA_DIAS = 5

    @staticmethod
    def conciliar_transacao(
        db,
        transaction
    ):

        # =========================
        # CRÉDITO
        # =========================

        if transaction.tipo == "CREDITO":

            inicio = (
                transaction.data_transacao
                - timedelta(
                    days=
                    AutoReconciliationService
                    .TOLERANCIA_DIAS
                )
            )

            fim = (
                transaction.data_transacao
                + timedelta(
                    days=
                    AutoReconciliationService
                    .TOLERANCIA_DIAS
                )
            )

            receivable = db.query(
                AccountsReceivable
            ).filter(
                AccountsReceivable.tenant_id
                ==
                transaction.tenant_id,

                AccountsReceivable.status
                ==
                "PENDENTE",

                AccountsReceivable.valor
                ==
                transaction.valor,

                AccountsReceivable.vencimento
                >= inicio,

                AccountsReceivable.vencimento
                <= fim
            ).first()

            if receivable:

                receivable.status = "RECEBIDO"

                receivable.data_recebimento = (
                    transaction.data_transacao
                )

                transaction.conciliado = True

                reconciliation = (
                    BankReconciliation(
                        bank_transaction_id=
                        transaction.id,

                        accounts_receivable_id=
                        receivable.id,

                        valor_conciliado=
                        transaction.valor,

                        data_conciliacao=
                        transaction.data_transacao,

                        observacao=
                        "Conciliação automática"
                    )
                )

                db.add(reconciliation)

                db.commit()

                return True

        # =========================
        # DÉBITO
        # =========================

        if transaction.tipo == "DEBITO":

            inicio = (
                transaction.data_transacao
                - timedelta(
                    days=
                    AutoReconciliationService
                    .TOLERANCIA_DIAS
                )
            )

            fim = (
                transaction.data_transacao
                + timedelta(
                    days=
                    AutoReconciliationService
                    .TOLERANCIA_DIAS
                )
            )

            payable = db.query(
                AccountsPayable
            ).filter(
                AccountsPayable.tenant_id
                ==
                transaction.tenant_id,

                AccountsPayable.status
                ==
                "PENDENTE",

                AccountsPayable.valor
                ==
                transaction.valor,

                AccountsPayable.vencimento
                >= inicio,

                AccountsPayable.vencimento
                <= fim
            ).first()

            if payable:

                payable.status = "PAGO"

                payable.data_pagamento = (
                    transaction.data_transacao
                )

                transaction.conciliado = True

                reconciliation = (
                    BankReconciliation(
                        bank_transaction_id=
                        transaction.id,

                        accounts_payable_id=
                        payable.id,

                        valor_conciliado=
                        transaction.valor,

                        data_conciliacao=
                        transaction.data_transacao,

                        observacao=
                        "Conciliação automática"
                    )
                )

                db.add(reconciliation)

                db.commit()

                return True

        return False