"""add processado to bank_transactions (a migration anterior 0aa3531f4ee5
tinha esse nome mas, por engano, adicionava a coluna em payroll_batches;
essa aqui corrige de verdade a tabela bank_transactions, que é o que o
model BankTransaction espera)

Revision ID: 3e1ba3201e6a
Revises: a7853f198313
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3e1ba3201e6a'
down_revision: Union[str, Sequence[str], None] = 'a7853f198313'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'bank_transactions',
        sa.Column(
            'processado',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )


def downgrade():
    op.drop_column(
        'bank_transactions',
        'processado'
    )
