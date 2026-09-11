"""add composite indexes tenant_id+status

Revision ID: afb2e5f0b0ec
Revises: cd73684652fd
Create Date: 2026-09-09 00:00:03.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'afb2e5f0b0ec'
down_revision: Union[str, Sequence[str], None] = 'cd73684652fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_index(
        'ix_accounts_payable_tenant_status',
        'accounts_payable',
        ['tenant_id', 'status']
    )

    op.create_index(
        'ix_accounts_receivable_tenant_status',
        'accounts_receivable',
        ['tenant_id', 'status']
    )


def downgrade():
    op.drop_index(
        'ix_accounts_receivable_tenant_status',
        table_name='accounts_receivable'
    )

    op.drop_index(
        'ix_accounts_payable_tenant_status',
        table_name='accounts_payable'
    )
