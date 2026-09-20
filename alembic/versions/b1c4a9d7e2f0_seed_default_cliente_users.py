"""seed default CLIENTE users for pre-existing clients

Revision ID: b1c4a9d7e2f0
Revises: fa3887bfd9e6
Create Date: 2026-09-12 00:00:00.000001

"""
import uuid

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.security import hash_password


revision: str = 'b1c4a9d7e2f0'
down_revision: Union[str, Sequence[str], None] = 'fa3887bfd9e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Login padrão criado para todo Client que já existia no banco antes do
# portal do CLIENTE existir (para não "perder" nenhum client sem acesso).
# O e-mail é gerado a partir do próprio id do client, então é único e
# estável. A senha é a mesma para todos — RECOMENDA-SE FORTEMENTE que o
# ADMIN troque a senha de cada client (ver PUT /clients/{id}/portal-access)
# antes de divulgar o link do portal.
DEFAULT_CLIENTE_SENHA = "Cliente@123"
DEFAULT_CLIENTE_EMAIL_DOMAIN = "bpo-system.local"


def upgrade():

    connection = op.get_bind()

    # Todo client que ainda não tem nenhum User com role = CLIENTE
    # apontando pra ele (LEFT JOIN ... IS NULL).
    clients_sem_login = connection.execute(
        sa.text(
            """
            SELECT c.id, c.tenant_id
            FROM clients c
            LEFT JOIN users u
                ON u.client_id = c.id AND u.role = 'CLIENTE'
            WHERE u.id IS NULL
            """
        )
    ).fetchall()

    if not clients_sem_login:
        return

    senha_hash = hash_password(DEFAULT_CLIENTE_SENHA)

    for client_id, tenant_id in clients_sem_login:

        email = f"cliente-{client_id}@{DEFAULT_CLIENTE_EMAIL_DOMAIN}"

        connection.execute(
            sa.text(
                """
                INSERT INTO users
                    (id, tenant_id, client_id, nome, email, senha_hash, role, ativo)
                VALUES
                    (:id, :tenant_id, :client_id, 'Acesso do Cliente', :email, :senha_hash, 'CLIENTE', true)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "client_id": str(client_id),
                "email": email,
                "senha_hash": senha_hash,
            }
        )


def downgrade():
    # Remove só os logins gerados automaticamente por esta migration
    # (identificáveis pelo domínio de e-mail e pelo nome padrão) — nunca
    # um login de CLIENTE que o ADMIN já tenha customizado depois.
    op.execute(
        sa.text(
            f"""
            DELETE FROM users
            WHERE role = 'CLIENTE'
              AND nome = 'Acesso do Cliente'
              AND email LIKE 'cliente-%@{DEFAULT_CLIENTE_EMAIL_DOMAIN}'
            """
        )
    )
