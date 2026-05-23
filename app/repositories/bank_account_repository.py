from sqlalchemy.orm import Session

from app.models.bank_account import (
    BankAccount
)


class BankAccountRepository:

    @staticmethod
    def create(db: Session, data: dict):

        account = BankAccount(**data)

        db.add(account)

        db.commit()

        db.refresh(account)

        return account

    @staticmethod
    def get_all(db: Session, tenant_id):

        return db.query(
            BankAccount
        ).filter(
            BankAccount.tenant_id == tenant_id
        ).all()

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        account_id
    ):

        return db.query(
            BankAccount
        ).filter(
            BankAccount.id == account_id,
            BankAccount.tenant_id == tenant_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        account,
        data: dict
    ):

        for key, value in data.items():
            setattr(account, key, value)

        db.commit()

        db.refresh(account)

        return account

    @staticmethod
    def delete(
        db: Session,
        account
    ):

        db.delete(account)

        db.commit()