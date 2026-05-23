"""add valor_transacao to payroll batch

Revision ID: af66a6c70ca8
Revises: 02f8f61fc4b8
Create Date: 2026-05-16 17:10:31.619866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af66a6c70ca8'
down_revision: Union[str, Sequence[str], None] = '02f8f61fc4b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.add_column(
        'payroll_batches',
        sa.Column(
            'valor_transacao',
            sa.Numeric(10, 2),
            nullable=True
        )
    )

    op.execute("""
        UPDATE payroll_batches
        SET valor_transacao = valor_total
    """)

    op.alter_column(
        'payroll_batches',
        'valor_transacao',
        nullable=False
    )


def downgrade():

    op.drop_column(
        'payroll_batches',
        'valor_transacao'
    )
