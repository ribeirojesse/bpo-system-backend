"""add super_admin and cliente roles to users

Revision ID: fa3887bfd9e6
Revises: ee1be962c531
Create Date: 2026-09-12 00:00:00.000000

"""
import uuid

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.security import hash_password


revision: str = 'fa3887bfd9e6'
down_revision: Union[str, Sequence[str], None] = 'ee1be962c531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Credenciais do primeiro SUPER_ADMIN, criado por esta migration de forma
# idempotente (ON CONFLICT DO NOTHING no e-mail). Recomenda-se trocar a
# senha após o primeiro login.
SUPER_ADMIN_EMAIL = "jesse@hooked.com"
SUPER_ADMIN_SENHA = "9GF5s3vgwA"
SUPER_ADMIN_NOME = "Jesse"


def upgrade():
    # 1) tenant_id passa a ser opcional: SUPER_ADMIN não pertence a
    # nenhum tenant.
    op.alter_column(
        'users',
        'tenant_id',
        nullable=True
    )

    # 2) client_id novo: só é preenchido quando role = CLIENTE (login do
    # cliente, restrito a UM client específico, não à carteira inteira).
    op.add_column(
        'users',
        sa.Column(
            'client_id',
            sa.UUID(),
            nullable=True
        )
    )

    op.create_foreign_key(
        'fk_users_client_id',
        'users',
        'clients',
        ['client_id'],
        ['id']
    )

    op.create_index(
        'ix_users_client_id',
        'users',
        ['client_id']
    )

    # 3) normaliza os roles existentes (hoje só existe a string livre
    # "admin", default do model antigo) para o valor padronizado.
    op.execute(
        """
        UPDATE users
        SET role = 'ADMIN'
        WHERE role IS NULL OR lower(role) = 'admin'
        """
    )

    # 4) trava o conjunto de roles válidos e a consistência entre
    # role / tenant_id / client_id:
    #   - SUPER_ADMIN: sem tenant, sem client
    #   - ADMIN: sempre com tenant, sem client (dono de uma carteira)
    #   - CLIENTE: sempre com tenant E com client (login restrito a 1 client)
    op.create_check_constraint(
        'ck_users_role_scope',
        'users',
        """
        (role = 'SUPER_ADMIN' AND tenant_id IS NULL AND client_id IS NULL)
        OR (role = 'ADMIN' AND tenant_id IS NOT NULL AND client_id IS NULL)
        OR (role = 'CLIENTE' AND tenant_id IS NOT NULL AND client_id IS NOT NULL)
        """
    )

    # 5) cria o primeiro SUPER_ADMIN (idempotente — se o e-mail já
    # existir, não faz nada). É o único jeito de nascer um usuário com
    # esse role, já que a criação de usuários agora exige um SUPER_ADMIN
    # autenticado (POST /admin/users, ver app/api/endpoints/admin_user.py
    # — o antigo POST /auth/register, público, foi removido).
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            INSERT INTO users
                (id, tenant_id, client_id, nome, email, senha_hash, role, ativo)
            VALUES
                (:id, NULL, NULL, :nome, :email, :senha_hash, 'SUPER_ADMIN', true)
            ON CONFLICT (email) DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "nome": SUPER_ADMIN_NOME,
            "email": SUPER_ADMIN_EMAIL,
            "senha_hash": hash_password(SUPER_ADMIN_SENHA),
        }
    )


def downgrade():
    op.execute(
        sa.text(
            "DELETE FROM users WHERE email = :email"
        ),
        {"email": SUPER_ADMIN_EMAIL}
    )

    op.drop_constraint(
        'ck_users_role_scope',
        'users',
        type_='check'
    )

    op.drop_index(
        'ix_users_client_id',
        table_name='users'
    )

    op.drop_constraint(
        'fk_users_client_id',
        'users',
        type_='foreignkey'
    )

    op.drop_column(
        'users',
        'client_id'
    )

    # ATENÇÃO: só funciona se não sobrar nenhum usuário com tenant_id
    # NULL (o próprio SUPER_ADMIN já foi removido acima).
    op.alter_column(
        'users',
        'tenant_id',
        nullable=False
    )
