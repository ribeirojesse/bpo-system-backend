from fastapi import HTTPException

from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction

from app.repositories.payroll_batch_repository import (
    PayrollBatchRepository
)


class PayrollBatchService:

    @staticmethod
    def _anexar_conta(db, current_user, batches):
        """Preenche `conta_nome` e `data_transacao` em cada lote a partir
        da transação do extrato que gerou a folha — é de lá que se sabe
        de qual conta o pagamento saiu (a folha não cria vínculo de
        conciliação)."""

        lotes = [batch for batch in batches if batch]

        if not lotes:
            return batches

        linhas = (
            db.query(
                BankTransaction.id,
                BankTransaction.data_transacao,
                BankAccount.banco,
                BankAccount.conta,
            )
            .outerjoin(
                BankAccount,
                BankAccount.id == BankTransaction.bank_account_id
            )
            .filter(
                BankTransaction.tenant_id == current_user.tenant_id,
                BankTransaction.id.in_([
                    batch.bank_transaction_id for batch in lotes
                ]),
            )
            .all()
        )

        dados = {
            transaction_id: (data, banco, conta)
            for transaction_id, data, banco, conta in linhas
        }

        for batch in lotes:

            data, banco, conta = dados.get(
                batch.bank_transaction_id,
                (None, None, None)
            )

            batch.data_transacao = data

            batch.conta_nome = (
                f"{banco} • {conta}" if banco else None
            )

        return batches

    @staticmethod
    def get_batches(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        batches = PayrollBatchRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

        return PayrollBatchService._anexar_conta(
            db,
            current_user,
            batches
        )

    @staticmethod
    def get_batch(
        db,
        current_user,
        batch_id
    ):

        batch = (
            PayrollBatchRepository.get_by_id(
                db,
                current_user.tenant_id,
                batch_id
            )
        )

        if not batch:

            raise HTTPException(
                status_code=404,
                detail="Lote não encontrado"
            )

        PayrollBatchService._anexar_conta(
            db,
            current_user,
            [batch]
        )

        return batch

    @staticmethod
    def get_by_transaction(
        db,
        current_user,
        transaction_id
    ):

        batch = (
            PayrollBatchRepository
            .get_by_transaction_id(
                db,
                current_user.tenant_id,
                transaction_id
            )
        )

        if not batch:
            return None

        PayrollBatchService._anexar_conta(
            db,
            current_user,
            [batch]
        )

        return batch