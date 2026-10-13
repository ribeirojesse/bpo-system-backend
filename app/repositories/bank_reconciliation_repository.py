from sqlalchemy.orm import Session

from app.models.bank_reconciliation import (
    BankReconciliation
)

from app.models.bank_transaction import (
    BankTransaction
)


class BankReconciliationRepository:

    @staticmethod
    def create(
        db: Session,
        data: dict
    ):

        reconciliation = BankReconciliation(
            **data
        )

        db.add(reconciliation)

        db.commit()

        db.refresh(reconciliation)

        return reconciliation

    @staticmethod
    def get_all(
        db: Session,
        tenant_id,
        skip: int = 0,
        limit: int = 100,
        client_id=None
    ):

        query = db.query(BankReconciliation).filter(
            BankReconciliation.tenant_id
            == tenant_id
        )

        # O cliente da conciliação é o da transação bancária vinculada.
        if client_id:
            query = query.join(
                BankTransaction,
                BankTransaction.id
                == BankReconciliation.bank_transaction_id
            ).filter(
                BankTransaction.client_id == client_id
            )

        # Mais recentes primeiro (antes sem ordem: o "limite" cortava
        # registros arbitrários da carteira inteira).
        return (
            query
            .order_by(
                BankReconciliation.data_conciliacao.desc(),
                BankReconciliation.id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def mapa_por_lancamento(db, tenant_id, ids, campo_fk):
        """Devolve {lancamento_id: reconciliation_id} pros ids
        informados. Usado pelas telas de Contas a Pagar/Receber pra saber
        quais linhas vieram de uma conciliação (e poder devolvê-las pra
        tela de Conciliação)."""

        if not ids:
            return {}

        campo = getattr(BankReconciliation, campo_fk)

        linhas = (
            db.query(campo, BankReconciliation.id)
            .filter(
                BankReconciliation.tenant_id == tenant_id,
                campo.in_(ids),
            )
            .all()
        )

        return {
            lancamento_id: reconciliation_id
            for lancamento_id, reconciliation_id in linhas
        }

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        reconciliation_id
    ):

        return (
            db.query(BankReconciliation)
            .filter(
                BankReconciliation.id
                == reconciliation_id,

                BankReconciliation.tenant_id
                == tenant_id
            )
            .first()
        )

    @staticmethod
    def delete(
        db: Session,
        reconciliation
    ):

        db.delete(reconciliation)

        db.commit()
