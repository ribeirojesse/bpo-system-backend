from sqlalchemy.orm import Session

from app.models.client import Client


class ClientRepository:

    @staticmethod
    def create(
        db: Session,
        data: dict
    ):

        client = Client(**data)

        db.add(client)

        db.commit()

        db.refresh(client)

        return client

    @staticmethod
    def get_all(
        db: Session,
        tenant_id
    ):

        return db.query(Client).filter(
            Client.tenant_id == tenant_id
        ).all()

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        client_id
    ):

        return db.query(Client).filter(
            Client.id == client_id,
            Client.tenant_id == tenant_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        client,
        data: dict
    ):

        for key, value in data.items():
            setattr(client, key, value)

        db.commit()

        db.refresh(client)

        return client

    @staticmethod
    def delete(
        db: Session,
        client
    ):

        db.delete(client)

        db.commit()