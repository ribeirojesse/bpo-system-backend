"""add ignorada to bank_transactions

Revision ID: ee1be962c531
Revises: afb2e5f0b0ec
Create Date: 2026-09-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ee1be962c531'
down_revision: Union[str, Sequence[str], None] = 'afb2e5f0b0ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'bank_transactions',
        sa.Column(
            'ignorada',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )


def downgrade():
    op.drop_column(
        'bank_transactions',
        'ignorada'
    )
