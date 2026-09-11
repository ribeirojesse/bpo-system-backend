from sqlalchemy.orm import Session

from app.models.bank_reconciliation import (
    BankReconciliation
)


class BankReconciliationRepository:

    @staticmethod
    def create(
        db: Session,
        data: dict
    ):

        reconciliation = BankReconciliation(
            **data
        )

        db.add(reconciliation)

        db.commit()

        db.refresh(reconciliation)

        return reconciliation

    @staticmethod
    def get_all(
        db: Session,
        tenant_id,
        skip: int = 0,
        limit: int = 100
    ):

        return (
            db.query(BankReconciliation)
            .filter(
                BankReconciliation.tenant_id
                == tenant_id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        reconciliation_id
    ):

        return (
            db.query(BankReconciliation)
            .filter(
                BankReconciliation.id
                == reconciliation_id,

                BankReconciliation.tenant_id
                == tenant_id
            )
            .first()
        )

    @staticmethod
    def delete(
        db: Session,
        reconciliation
    ):

        db.delete(reconciliation)

        db.commit()
