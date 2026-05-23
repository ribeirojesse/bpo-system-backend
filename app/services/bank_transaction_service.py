import hashlib

from fastapi import HTTPException

from app.repositories.client_repository import (
    ClientRepository
)

from app.repositories.bank_account_repository import (
    BankAccountRepository
)

from app.repositories.bank_transaction_repository import (
    BankTransactionRepository
)


class BankTransactionService:

    @staticmethod
    def gerar_hash(
        data,
        valor,
        descricao,
        conta
    ):

        conteudo = (
            f"{data}_{valor}_{descricao}_{conta}"
        )

        return hashlib.md5(
            conteudo.encode()
        ).hexdigest()

    @staticmethod
    def create_transaction(
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

        account = BankAccountRepository.get_by_id(
            db,
            current_user.tenant_id,
            data.bank_account_id
        )

        if not account:

            raise HTTPException(
                status_code=404,
                detail="Conta bancária não encontrada"
            )

        payload = data.model_dump()

        payload["tenant_id"] = (
            current_user.tenant_id
        )

        payload["hash_transacao"] = (
            BankTransactionService.gerar_hash(
                data.data_transacao,
                data.valor,
                data.descricao,
                data.bank_account_id
            )
        )

        payload["conciliado"] = False

        return BankTransactionRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_transactions(
        db,
        current_user
    ):

        return BankTransactionRepository.get_all(
            db,
            current_user.tenant_id
        )

    @staticmethod
    def get_transaction(
        db,
        current_user,
        transaction_id
    ):

        transaction = (
            BankTransactionRepository.get_by_id(
                db,
                current_user.tenant_id,
                transaction_id
            )
        )

        if not transaction:

            raise HTTPException(
                status_code=404,
                detail="Transação não encontrada"
            )

        return transaction

    @staticmethod
    def update_transaction(
        db,
        current_user,
        transaction_id,
        data
    ):

        transaction = (
            BankTransactionService.get_transaction(
                db,
                current_user,
                transaction_id
            )
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return BankTransactionRepository.update(
            db,
            transaction,
            payload
        )

    @staticmethod
    def delete_transaction(
        db,
        current_user,
        transaction_id
    ):

        transaction = (
            BankTransactionService.get_transaction(
                db,
                current_user,
                transaction_id
            )
        )

        BankTransactionRepository.delete(
            db,
            transaction
        )

        return {
            "message":
            "Transação removida"
        }