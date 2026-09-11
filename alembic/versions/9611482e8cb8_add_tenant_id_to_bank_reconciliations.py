"""add tenant_id to bank_reconciliations

Revision ID: 9611482e8cb8
Revises: 26f26d831515
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9611482e8cb8'
down_revision: Union[str, Sequence[str], None] = '26f26d831515'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) adiciona a coluna nullable
    op.add_column(
        'bank_reconciliations',
        sa.Column(
            'tenant_id',
            sa.UUID(),
            nullable=True
        )
    )

    # 2) faz o backfill a partir da transação bancária vinculada
    op.execute(
        """
        UPDATE bank_reconciliations br
        SET tenant_id = bt.tenant_id
        FROM bank_transactions bt
        WHERE br.bank_transaction_id = bt.id
        """
    )

    # 3) agora que todo mundo tem tenant_id, torna a coluna obrigatória
    op.alter_column(
        'bank_reconciliations',
        'tenant_id',
        nullable=False
    )

    op.create_foreign_key(
        'fk_bank_reconciliations_tenant_id',
        'bank_reconciliations',
        'tenants',
        ['tenant_id'],
        ['id']
    )

    op.create_index(
        'ix_bank_reconciliations_tenant_id',
        'bank_reconciliations',
        ['tenant_id']
    )


def downgrade():
    op.drop_index(
        'ix_bank_reconciliations_tenant_id',
        table_name='bank_reconciliations'
    )

    op.drop_constraint(
        'fk_bank_reconciliations_tenant_id',
        'bank_reconciliations',
        type_='foreignkey'
    )

    op.drop_column(
        'bank_reconciliations',
        'tenant_id'
    )
