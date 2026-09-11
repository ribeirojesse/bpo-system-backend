from sqlalchemy.orm import Session

from app.models.bank_transaction import (
    BankTransaction
)


class BankTransactionRepository:

    @staticmethod
    def create(db: Session, data: dict):

        transaction = BankTransaction(**data)

        db.add(transaction)

        db.commit()

        db.refresh(transaction)

        return transaction

    @staticmethod
    def get_all(
        db: Session,
        tenant_id,
        skip: int = 0,
        limit: int = 100
    ):

        return (
            db.query(BankTransaction)
            .filter(
                BankTransaction.tenant_id == tenant_id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        transaction_id
    ):

        return db.query(
            BankTransaction
        ).filter(
            BankTransaction.id == transaction_id,
            BankTransaction.tenant_id == tenant_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        transaction,
        data: dict
    ):

        for key, value in data.items():
            setattr(transaction, key, value)

        db.commit()

        db.refresh(transaction)

        return transaction

    @staticmethod
    def delete(
        db: Session,
        transaction
    ):

        db.delete(transaction)

        db.commit()