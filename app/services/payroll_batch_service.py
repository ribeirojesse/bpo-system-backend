from fastapi import HTTPException

from app.repositories.payroll_batch_repository import (
    PayrollBatchRepository
)


class PayrollBatchService:

    @staticmethod
    def get_batches(
        db,
        current_user
    ):

        return (
            PayrollBatchRepository.get_all(
                db,
                current_user.tenant_id
            )
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

        return batch