"""create leads table

Contatos do formulário "Agendar diagnóstico" do site (landing page),
com os parâmetros de origem dos anúncios (utm_*, gclid, fbclid...).

Revision ID: f1d2c3b4a5e6
Revises: e7a1c3d9f2b4
Create Date: 2026-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f1d2c3b4a5e6'
down_revision: Union[str, Sequence[str], None] = 'e7a1c3d9f2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'leads',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('empresa', sa.String(length=160), nullable=False),
        sa.Column('whatsapp', sa.String(length=20), nullable=False),
        sa.Column('volume', sa.String(length=40), nullable=True),
        sa.Column('mensagem', sa.String(length=1000), nullable=True),
        sa.Column('pagina', sa.String(length=200), nullable=True),
        sa.Column('utm_source', sa.String(length=200), nullable=True),
        sa.Column('utm_medium', sa.String(length=200), nullable=True),
        sa.Column('utm_campaign', sa.String(length=200), nullable=True),
        sa.Column(
            'atribuicao',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        ),
        sa.Column(
            'status',
            sa.String(length=20),
            server_default='NOVO',
            nullable=False
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_leads_created_at', 'leads', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_leads_created_at', table_name='leads')
    op.drop_table('leads')
