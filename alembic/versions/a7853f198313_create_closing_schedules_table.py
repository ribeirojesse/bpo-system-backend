"""create closing_schedules table

Revision ID: a7853f198313
Revises: d93a1f5c7b2e
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7853f198313'
down_revision: Union[str, Sequence[str], None] = 'd93a1f5c7b2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'closing_schedules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('titulo', sa.String(), nullable=False),
        sa.Column('descricao', sa.String(), nullable=True),
        sa.Column('competencia', sa.String(), nullable=True),
        sa.Column('data_vencimento', sa.Date(), nullable=False),
        sa.Column(
            'dias_lembrete',
            sa.Integer(),
            server_default='3',
            nullable=False
        ),
        sa.Column(
            'status',
            sa.String(),
            server_default='PENDENTE',
            nullable=False
        ),
        sa.Column('data_conclusao', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        'ix_closing_schedules_tenant_status',
        'closing_schedules',
        ['tenant_id', 'status']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_closing_schedules_tenant_status',
        table_name='closing_schedules'
    )

    op.drop_table('closing_schedules')
