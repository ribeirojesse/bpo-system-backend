from fastapi import HTTPException

from app.repositories.client_repository import (
    ClientRepository
)


class ClientService:

    @staticmethod
    def create_client(
        db,
        current_user,
        data
    ):

        payload = data.model_dump()

        payload["tenant_id"] = current_user.tenant_id

        return ClientRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_clients(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return ClientRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

    @staticmethod
    def get_client(
        db,
        current_user,
        client_id
    ):

        client = ClientRepository.get_by_id(
            db,
            current_user.tenant_id,
            client_id
        )

        if not client:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        return client

    @staticmethod
    def update_client(
        db,
        current_user,
        client_id,
        data
    ):

        client = ClientService.get_client(
            db,
            current_user,
            client_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return ClientRepository.update(
            db,
            client,
            payload
        )

    @staticmethod
    def delete_client(
        db,
        current_user,
        client_id
    ):

        client = ClientService.get_client(
            db,
            current_user,
            client_id
        )

        ClientRepository.delete(
            db,
            client
        )

        return {
            "message": "Cliente removido"
        }