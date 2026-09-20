"""scope bank_transaction hash to tenant

Revision ID: 841e94f0a0a5
Revises: 9611482e8cb8
Create Date: 2026-09-09 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '841e94f0a0a5'
down_revision: Union[str, Sequence[str], None] = '9611482e8cb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Remove a constraint de unicidade global em hash_transacao
    # (nome gerado automaticamente pelo Postgres na criação original).
    # IF EXISTS evita quebrar caso o nome real seja diferente.
    op.execute(
        "ALTER TABLE bank_transactions "
        "DROP CONSTRAINT IF EXISTS "
        "bank_transactions_hash_transacao_key"
    )

    op.create_unique_constraint(
        'uq_bank_transactions_tenant_hash',
        'bank_transactions',
        ['tenant_id', 'hash_transacao']
    )


def downgrade():
    op.drop_constraint(
        'uq_bank_transactions_tenant_hash',
        'bank_transactions',
        type_='unique'
    )

    op.create_unique_constraint(
        'bank_transactions_hash_transacao_key',
        'bank_transactions',
        ['hash_transacao']
    )
