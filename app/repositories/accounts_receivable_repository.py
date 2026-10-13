from sqlalchemy.orm import Session

from app.models.accounts_receivable import (
    AccountsReceivable
)


class AccountsReceivableRepository:

    @staticmethod
    def create(db: Session, data: dict):

        receivable = AccountsReceivable(**data)

        db.add(receivable)

        db.commit()

        db.refresh(receivable)

        return receivable

    @staticmethod
    def get_all(
        db: Session,
        tenant_id,
        skip: int = 0,
        limit: int = 100,
        client_id=None
    ):

        query = db.query(AccountsReceivable).filter(
            AccountsReceivable.tenant_id == tenant_id
        )

        # Filtra no banco (antes a tela buscava só os primeiros N da
        # carteira inteira e filtrava o cliente no navegador, então
        # clientes com lançamentos "fora" dessa janela apareciam vazios).
        if client_id:
            query = query.filter(
                AccountsReceivable.client_id == client_id
            )

        return (
            query
            .order_by(
                AccountsReceivable.vencimento.desc(),
                AccountsReceivable.id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        receivable_id
    ):

        return db.query(
            AccountsReceivable
        ).filter(
            AccountsReceivable.id == receivable_id,
            AccountsReceivable.tenant_id == tenant_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        receivable,
        data: dict
    ):

        for key, value in data.items():
            setattr(receivable, key, value)

        db.commit()

        db.refresh(receivable)

        return receivable

    @staticmethod
    def delete(
        db: Session,
        receivable
    ):

        db.delete(receivable)

        db.commit()