from fastapi import HTTPException

from app.core.security import hash_password

from app.models.user import User

from app.repositories.client_repository import (
    ClientRepository
)

from app.repositories.user_repository import (
    UserRepository
)


class ClientService:

    @staticmethod
    def create_client(
        db,
        current_user,
        data
    ):

        payload = data.model_dump()

        payload["tenant_id"] = current_user.tenant_id

        return ClientRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_clients(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return ClientRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

    @staticmethod
    def get_client(
        db,
        current_user,
        client_id
    ):

        client = ClientRepository.get_by_id(
            db,
            current_user.tenant_id,
            client_id
        )

        if not client:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        return client

    @staticmethod
    def update_client(
        db,
        current_user,
        client_id,
        data
    ):

        client = ClientService.get_client(
            db,
            current_user,
            client_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return ClientRepository.update(
            db,
            client,
            payload
        )

    @staticmethod
    def delete_client(
        db,
        current_user,
        client_id
    ):

        client = ClientService.get_client(
            db,
            current_user,
            client_id
        )

        ClientRepository.delete(
            db,
            client
        )

        return {
            "message": "Cliente removido"
        }

    # ------------------------------------------------------------------
    # Acesso do CLIENTE ao portal.
    #
    # Todo Client já tem um login CLIENTE criado automaticamente pela
    # migration b1c4a9d7e2f0 (ou pelo próprio ADMIN, se o client foi
    # criado depois dela). Estes métodos deixam o ADMIN ver qual é o
    # e-mail atual e, se quiser, trocar e-mail/senha desse login — nunca
    # criam um segundo login para o mesmo client.
    # ------------------------------------------------------------------

    @staticmethod
    def get_portal_access(
        db,
        current_user,
        client_id
    ):

        # Garante que o client pertence ao tenant do ADMIN logado.
        client = ClientService.get_client(
            db,
            current_user,
            client_id
        )

        cliente_user = UserRepository.get_cliente_by_client_id(
            db,
            client.id
        )

        if not cliente_user:
            return {
                "has_access": False,
                "email": None,
            }

        return {
            "has_access": True,
            "email": cliente_user.email,
        }

    @staticmethod
    def set_portal_access(
        db,
        current_user,
        client_id,
        data
    ):

        client = ClientService.get_client(
            db,
            current_user,
            client_id
        )

        payload = data.model_dump(exclude_unset=True)

        password = payload.pop("password", None)

        if "email" in payload:

            existing = UserRepository.get_by_email(
                db,
                payload["email"]
            )

            cliente_user_atual = UserRepository.get_cliente_by_client_id(
                db,
                client.id
            )

            if existing and (
                not cliente_user_atual
                or existing.id != cliente_user_atual.id
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Email já cadastrado"
                )

        if password:
            payload["senha_hash"] = hash_password(password)

        cliente_user = UserRepository.get_cliente_by_client_id(
            db,
            client.id
        )

        if cliente_user:

            UserRepository.update(
                db,
                cliente_user,
                payload
            )

        else:

            # Client sem login (não deveria acontecer depois da migration
            # de seed, mas cobre o caso de um client criado manualmente
            # no banco, fora da API).
            novo_email = payload.get("email")

            if not novo_email:
                raise HTTPException(
                    status_code=400,
                    detail="Informe um e-mail para criar o acesso"
                )

            novo_user = User(
                tenant_id=client.tenant_id,
                client_id=client.id,
                nome="Acesso do Cliente",
                email=novo_email,
                senha_hash=payload.get(
                    "senha_hash",
                    hash_password("Cliente@123")
                ),
                role="CLIENTE"
            )

            cliente_user = UserRepository.create(db, novo_user)

        return {
            "has_access": True,
            "email": cliente_user.email,
        }
