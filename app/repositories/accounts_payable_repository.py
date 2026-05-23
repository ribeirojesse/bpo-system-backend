from sqlalchemy.orm import Session

from app.models.accounts_payable import (
    AccountsPayable
)


class AccountsPayableRepository:

    @staticmethod
    def create(db: Session, data: dict):

        payable = AccountsPayable(**data)

        db.add(payable)

        db.commit()

        db.refresh(payable)

        return payable

    @staticmethod
    def get_all(db: Session, tenant_id):

        return db.query(
            AccountsPayable
        ).filter(
            AccountsPayable.tenant_id == tenant_id
        ).all()

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        payable_id
    ):

        return db.query(
            AccountsPayable
        ).filter(
            AccountsPayable.id == payable_id,
            AccountsPayable.tenant_id == tenant_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        payable,
        data: dict
    ):

        for key, value in data.items():
            setattr(payable, key, value)

        db.commit()

        db.refresh(payable)

        return payable

    @staticmethod
    def delete(
        db: Session,
        payable
    ):

        db.delete(payable)

        db.commit()