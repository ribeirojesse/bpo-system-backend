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
    def get_all(db: Session):

        return db.query(
            BankReconciliation
        ).all()