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
        tenant_id,
        data,
        valor,
        descricao,
        conta
    ):

        # Inclui o tenant_id no conteúdo do hash para que a
        # deduplicação nunca cruze dados entre tenants diferentes.
        conteudo = (
            f"{tenant_id}_{data}_{valor}_{descricao}_{conta}"
        )

        return hashlib.sha256(
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
                current_user.tenant_id,
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
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return BankTransactionRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
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

    @staticmethod
    def ignore_transaction(
        db,
        current_user,
        transaction_id
    ):
        """Arquiva uma transação sem lançamento correspondente (ex.:
        transferência entre contas do próprio cliente) — ela some da
        lista de pendências da Conciliação sem virar uma conta a
        pagar/receber."""

        transaction = (
            BankTransactionService.get_transaction(
                db,
                current_user,
                transaction_id
            )
        )

        if transaction.conciliado:
            raise HTTPException(
                status_code=400,
                detail="Essa transação já foi conciliada"
            )

        if transaction.processado:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa transação já foi "
                    "processada via folha "
                    "de pagamento"
                )
            )

        transaction.ignorada = True

        db.commit()

        db.refresh(transaction)

        return transaction

    @staticmethod
    def restore_transaction(
        db,
        current_user,
        transaction_id
    ):
        """Desfaz o arquivamento — a transação volta a aparecer na lista
        de pendências da Conciliação."""

        transaction = (
            BankTransactionService.get_transaction(
                db,
                current_user,
                transaction_id
            )
        )

        transaction.ignorada = False

        db.commit()

        db.refresh(transaction)

        return transaction
