from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.tenant import Tenant
from app.models.client import Client


class UserRepository:

    @staticmethod
    def get_by_email(db: Session, email: str):

        return db.query(User).filter(
            User.email == email
        ).first()

    @staticmethod
    def get_admin_by_id(db: Session, user_id):

        return db.query(User).filter(
            User.id == user_id,
            User.role == "ADMIN"
        ).first()

    @staticmethod
    def get_cliente_by_client_id(db: Session, client_id):

        return db.query(User).filter(
            User.client_id == client_id,
            User.role == "CLIENTE"
        ).first()

    @staticmethod
    def create(db: Session, user: User):

        db.add(user)

        db.commit()

        db.refresh(user)

        return user

    @staticmethod
    def update(db: Session, user: User, data: dict):

        for key, value in data.items():
            setattr(user, key, value)

        db.commit()

        db.refresh(user)

        return user

    @staticmethod
    def delete(db: Session, user: User):

        db.delete(user)

        db.commit()

    @staticmethod
    def list_admins_with_client_count(db: Session):
        """
        Todos os usuários ADMIN (donos de carteira), com o nome do
        próprio tenant e a contagem de clients daquele tenant.
        """

        counts = dict(
            db.query(
                Client.tenant_id,
                func.count(Client.id)
            )
            .group_by(Client.tenant_id)
            .all()
        )

        rows = (
            db.query(User, Tenant)
            .join(Tenant, Tenant.id == User.tenant_id)
            .filter(User.role == "ADMIN")
            .order_by(User.nome)
            .all()
        )

        result = []

        for user, tenant in rows:

            result.append({
                "id": user.id,
                "nome": user.nome,
                "email": user.email,
                "ativo": user.ativo,
                "tenant_id": tenant.id,
                "tenant_nome": tenant.nome,
                "clientes_count": counts.get(tenant.id, 0),
            })

        return result
