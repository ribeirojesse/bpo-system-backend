import hashlib

from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from app.models.bank_reconciliation import BankReconciliation

from app.models.payroll_batch import PayrollBatch

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

        if not account or account.client_id != data.client_id:

            raise HTTPException(
                status_code=404,
                detail="Conta bancária não encontrada para este cliente"
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

        payload["ignorada"] = False

        payload["processado"] = False

        try:

            return BankTransactionRepository.create(
                db,
                payload
            )

        except IntegrityError:

            # uq_bank_transactions_tenant_hash: mesma data + valor +
            # descrição + conta já existe (ex.: já veio pelo OFX).
            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Já existe uma transação idêntica nessa conta "
                    "(mesma data, valor e descrição)."
                )
            )

    @staticmethod
    def get_transactions(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100,
        client_id=None
    ):

        return BankTransactionRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit,
            client_id
        )

    @staticmethod
    def motivo_bloqueio_exclusao(db, transaction):
        """Por que essa transação NÃO pode ser apagada (ou None se pode).
        Qualquer coisa que aponte pra ela no banco impediria o DELETE
        (erro de FK) — melhor recusar com uma mensagem clara."""

        if transaction.conciliado:
            return (
                "Já foi conciliada. Desfaça a conciliação "
                "antes de excluir."
            )

        if transaction.processado:
            return "Já foi processada via folha de pagamento."

        tem_conciliacao = db.query(BankReconciliation.id).filter(
            BankReconciliation.bank_transaction_id == transaction.id
        ).first()

        if tem_conciliacao:
            return (
                "Tem uma conciliação vinculada. Desfaça a "
                "conciliação antes de excluir."
            )

        tem_folha = db.query(PayrollBatch.id).filter(
            PayrollBatch.bank_transaction_id == transaction.id
        ).first()

        if tem_folha:
            return "Tem um lote de folha de pagamento vinculado."

        return None

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

        campos_financeiros = {
            "bank_account_id",
            "data_transacao",
            "valor",
            "tipo",
        }

        mudou_financeiro = any(
            campo in payload
            and payload[campo] is not None
            and payload[campo] != getattr(transaction, campo)
            for campo in campos_financeiros
        )

        # Conciliada/processada: o valor, a data, o tipo e a conta já
        # estão "amarrados" a um lançamento pago/recebido ou à folha —
        # só descrição/documento podem mudar.
        if mudou_financeiro and (
            transaction.conciliado or transaction.processado
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Essa transação já foi conciliada/processada: "
                    "só a descrição e o documento podem ser editados. "
                    "Desfaça a conciliação para alterar valor, data, "
                    "tipo ou conta."
                )
            )

        if payload.get("bank_account_id"):

            account = BankAccountRepository.get_by_id(
                db,
                current_user.tenant_id,
                payload["bank_account_id"]
            )

            if not account or account.client_id != transaction.client_id:
                raise HTTPException(
                    status_code=404,
                    detail="Conta bancária não encontrada para este cliente"
                )

        # Campos nulos no formulário = "não mexer".
        payload = {
            k: v for k, v in payload.items()
            if v is not None or k == "documento"
        }

        if mudou_financeiro or "descricao" in payload:

            payload["hash_transacao"] = (
                BankTransactionService.gerar_hash(
                    current_user.tenant_id,
                    payload.get("data_transacao", transaction.data_transacao),
                    payload.get("valor", transaction.valor),
                    payload.get("descricao", transaction.descricao),
                    payload.get("bank_account_id", transaction.bank_account_id)
                )
            )

        try:

            return BankTransactionRepository.update(
                db,
                transaction,
                payload
            )

        except IntegrityError:

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Já existe uma transação idêntica nessa conta "
                    "(mesma data, valor e descrição)."
                )
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

        motivo = BankTransactionService.motivo_bloqueio_exclusao(
            db,
            transaction
        )

        if motivo:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível excluir: {motivo}"
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


    @staticmethod
    def bulk_action(
        db,
        current_user,
        ids,
        acao
    ):
        """Excluir / ignorar / reabrir várias transações de uma vez.

        Faz o que dá e devolve o resto em "recusadas" com o motivo (ex.:
        uma já conciliada no meio da seleção não impede as outras). Tudo
        numa transação só de banco: ou grava o lote inteiro, ou nada."""

        transactions = BankTransactionRepository.get_many_by_ids(
            db,
            current_user.tenant_id,
            ids
        )

        encontradas = {t.id for t in transactions}

        recusadas = [
            {"id": i, "descricao": None, "motivo": "Transação não encontrada"}
            for i in ids
            if i not in encontradas
        ]

        processadas = 0

        for transaction in transactions:

            if acao == "EXCLUIR":
                motivo = BankTransactionService.motivo_bloqueio_exclusao(
                    db,
                    transaction
                )

            elif acao == "IGNORAR":
                motivo = (
                    "Já foi conciliada" if transaction.conciliado
                    else "Já foi processada via folha de pagamento"
                    if transaction.processado
                    else None
                )

            else:
                motivo = None

            if motivo:
                recusadas.append({
                    "id": transaction.id,
                    "descricao": transaction.descricao,
                    "motivo": motivo,
                })
                continue

            if acao == "EXCLUIR":
                db.delete(transaction)

            elif acao == "IGNORAR":
                transaction.ignorada = True

            else:
                transaction.ignorada = False

            processadas += 1

        db.commit()

        return {
            "acao": acao,
            "processadas": processadas,
            "recusadas": recusadas,
        }
