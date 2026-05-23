from fastapi import HTTPException

from app.repositories.client_repository import (
    ClientRepository
)

from app.repositories.financial_contact_repository import (
    FinancialContactRepository
)


class FinancialContactService:

    @staticmethod
    def create_contact(
        db,
        current_user,
        data
    ):

        client = ClientRepository.get_by_id(
            db,
            current_user.tenant_id,
            data.client_id
        )

        if not client:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        payload = data.model_dump()

        payload["tenant_id"] = current_user.tenant_id

        return FinancialContactRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_contacts(
        db,
        current_user
    ):

        return FinancialContactRepository.get_all(
            db,
            current_user.tenant_id
        )

    @staticmethod
    def get_contact(
        db,
        current_user,
        contact_id
    ):

        contact = FinancialContactRepository.get_by_id(
            db,
            current_user.tenant_id,
            contact_id
        )

        if not contact:
            raise HTTPException(
                status_code=404,
                detail="Contato não encontrado"
            )

        return contact

    @staticmethod
    def update_contact(
        db,
        current_user,
        contact_id,
        data
    ):

        contact = FinancialContactService.get_contact(
            db,
            current_user,
            contact_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return FinancialContactRepository.update(
            db,
            contact,
            payload
        )

    @staticmethod
    def delete_contact(
        db,
        current_user,
        contact_id
    ):

        contact = FinancialContactService.get_contact(
            db,
            current_user,
            contact_id
        )

        FinancialContactRepository.delete(
            db,
            contact
        )

        return {
            "message": "Contato removido"
        }