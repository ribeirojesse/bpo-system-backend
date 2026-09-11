from app.models.payroll_batch import (
    PayrollBatch
)


class PayrollBatchRepository:

    @staticmethod
    def get_all(
        db,
        tenant_id,
        skip: int = 0,
        limit: int = 100
    ):

        return (
            db.query(PayrollBatch)
            .filter(
                PayrollBatch.tenant_id
                == tenant_id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(
        db,
        tenant_id,
        batch_id
    ):

        return (
            db.query(PayrollBatch)
            .filter(
                PayrollBatch.id == batch_id,
                PayrollBatch.tenant_id
                == tenant_id
            )
            .first()
        )

    @staticmethod
    def get_by_transaction_id(
        db,
        tenant_id,
        transaction_id
    ):

        return (
            db.query(PayrollBatch)
            .filter(
                PayrollBatch.bank_transaction_id
                == transaction_id,
                PayrollBatch.tenant_id
                == tenant_id
            )
            .first()
        )