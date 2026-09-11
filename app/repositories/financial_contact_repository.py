from sqlalchemy.orm import Session

from app.models.financial_contact import (
    FinancialContact
)


class FinancialContactRepository:

    @staticmethod
    def create(db: Session, data: dict):

        contact = FinancialContact(**data)

        db.add(contact)

        db.commit()

        db.refresh(contact)

        return contact

    @staticmethod
    def get_all(
        db: Session,
        tenant_id,
        skip: int = 0,
        limit: int = 100
    ):

        return (
            db.query(FinancialContact)
            .filter(
                FinancialContact.tenant_id == tenant_id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        contact_id
    ):

        return db.query(
            FinancialContact
        ).filter(
            FinancialContact.id == contact_id,
            FinancialContact.tenant_id == tenant_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        contact,
        data: dict
    ):

        for key, value in data.items():
            setattr(contact, key, value)

        db.commit()

        db.refresh(contact)

        return contact

    @staticmethod
    def delete(
        db: Session,
        contact
    ):

        db.delete(contact)

        db.commit()