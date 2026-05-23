"""add processado to bank_transactions

Revision ID: 0aa3531f4ee5
Revises: af66a6c70ca8
Create Date: 2026-05-17 02:34:12.081015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0aa3531f4ee5'
down_revision: Union[str, Sequence[str], None] = 'af66a6c70ca8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'payroll_batches',
        sa.Column(
            'processado',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )

def downgrade():
    op.drop_column(
        'payroll_batches',
        'processado'
    )
