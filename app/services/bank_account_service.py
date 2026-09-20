from fastapi import HTTPException

from app.repositories.client_repository import (
    ClientRepository
)

from app.repositories.bank_account_repository import (
    BankAccountRepository
)


class BankAccountService:

    @staticmethod
    def create_account(
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

        return BankAccountRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_accounts(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return BankAccountRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

    @staticmethod
    def get_account(
        db,
        current_user,
        account_id
    ):

        account = BankAccountRepository.get_by_id(
            db,
            current_user.tenant_id,
            account_id
        )

        if not account:
            raise HTTPException(
                status_code=404,
                detail="Conta bancária não encontrada"
            )

        return account

    @staticmethod
    def update_account(
        db,
        current_user,
        account_id,
        data
    ):

        account = BankAccountService.get_account(
            db,
            current_user,
            account_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return BankAccountRepository.update(
            db,
            account,
            payload
        )

    @staticmethod
    def delete_account(
        db,
        current_user,
        account_id
    ):

        account = BankAccountService.get_account(
            db,
            current_user,
            account_id
        )

        BankAccountRepository.delete(
            db,
            account
        )

        return {
            "message": "Conta removida"
        }