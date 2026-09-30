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
        limit: int = 100,
        client_id=None
    ):

        query = db.query(BankTransaction).filter(
            BankTransaction.tenant_id == tenant_id
        )

        if client_id:
            query = query.filter(
                BankTransaction.client_id == client_id
            )

        # ORDER BY explícito: sem ele o Postgres devolve as linhas em
        # ordem física, que muda a cada UPDATE/DELETE — combinado com o
        # LIMIT, isso fazia transações "entrarem e saírem" da tela
        # (ex.: excluir uma fazia o contador de recebimentos subir).
        return (
            query
            .order_by(
                BankTransaction.data_transacao.desc(),
                BankTransaction.id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_many_by_ids(
        db: Session,
        tenant_id,
        ids
    ):

        return db.query(BankTransaction).filter(
            BankTransaction.id.in_(ids),
            BankTransaction.tenant_id == tenant_id
        ).all()

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