from fastapi import HTTPException

from sqlalchemy import func

from app.core.security import hash_password

from app.models.tenant import Tenant
from app.models.client import Client
from app.models.user import User

from app.repositories.user_repository import UserRepository


class AdminUserService:

    @staticmethod
    def create_user(db, data):

        existing = UserRepository.get_by_email(db, data.email)

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email já cadastrado"
            )

        tenant = Tenant(
            nome=data.tenant_nome,
            email=data.email
        )

        db.add(tenant)

        db.flush()

        user = User(
            tenant_id=tenant.id,
            nome=data.nome,
            email=data.email,
            senha_hash=hash_password(data.password),
            role="ADMIN"
        )

        UserRepository.create(db, user)

        return {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "ativo": user.ativo,
            "tenant_id": tenant.id,
            "tenant_nome": tenant.nome,
            "clientes_count": 0,
        }

    @staticmethod
    def list_users(db):

        return UserRepository.list_admins_with_client_count(db)

    @staticmethod
    def update_user(db, user_id, data):

        user = UserRepository.get_admin_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )

        payload = data.model_dump(exclude_unset=True)

        password = payload.pop("password", None)

        if password:
            payload["senha_hash"] = hash_password(password)

        if "email" in payload:

            existing = UserRepository.get_by_email(db, payload["email"])

            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=400,
                    detail="Email já cadastrado"
                )

        UserRepository.update(db, user, payload)

        clientes_count = db.query(func.count(Client.id)).filter(
            Client.tenant_id == user.tenant_id
        ).scalar()

        return {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "ativo": user.ativo,
            "tenant_id": user.tenant_id,
            "tenant_nome": user.tenant.nome,
            "clientes_count": clientes_count,
        }

    @staticmethod
    def delete_user(db, user_id):

        user = UserRepository.get_admin_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )

        # Remove só o login do usuário (role ADMIN). O tenant e os
        # clients que ele já tinha criado permanecem no banco — não são
        # apagados em cascata. Apagar a carteira inteira junto seria uma
        # ação separada e mais destrutiva, fora do escopo deste CRUD.
        UserRepository.delete(db, user)

        return {
            "message": "Usuário removido"
        }
