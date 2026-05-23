from fastapi import HTTPException

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


class BankReconciliationService:

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

            payable.status = "PAGO"

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

            receivable.status = "RECEBIDO"

        transaction.conciliado = True

        reconciliation = (
            BankReconciliationRepository.create(
                db,
                data.model_dump()
            )
        )

        db.commit()

        return reconciliation
    
    @staticmethod
    def get_reconciliations(db):

        return (
            BankReconciliationRepository.get_all(
                db
            )
        )