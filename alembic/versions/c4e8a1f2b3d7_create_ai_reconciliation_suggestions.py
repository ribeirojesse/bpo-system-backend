"""create ai_reconciliation_suggestions table

Sugestões de conciliação geradas pela IA (API do Claude), guardadas por
transação bancária pra não chamar a IA de novo a cada abertura da tela.

Revision ID: c4e8a1f2b3d7
Revises: 3e1ba3201e6a
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e8a1f2b3d7'
down_revision: Union[str, Sequence[str], None] = '3e1ba3201e6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_reconciliation_suggestions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('bank_transaction_id', sa.UUID(), nullable=False),
        sa.Column('tipo_match', sa.String(), nullable=True),
        sa.Column('match_id', sa.UUID(), nullable=True),
        sa.Column('financial_contact_id', sa.UUID(), nullable=True),
        sa.Column('novo_fornecedor_nome', sa.String(), nullable=True),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('subcategory_id', sa.UUID(), nullable=True),
        sa.Column('competencia', sa.String(), nullable=True),
        sa.Column('confianca', sa.String(), nullable=False),
        sa.Column('justificativa', sa.String(), nullable=True),
        sa.Column('modelo', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(
            ['bank_transaction_id'],
            ['bank_transactions.id'],
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['financial_contact_id'],
            ['financial_contacts.id'],
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['category_id'],
            ['expense_categories.id'],
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['subcategory_id'],
            ['expense_subcategories.id'],
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'bank_transaction_id',
            name='uq_ai_reconciliation_suggestions_transaction'
        )
    )

    op.create_index(
        'ix_ai_reconciliation_suggestions_tenant_id',
        'ai_reconciliation_suggestions',
        ['tenant_id']
    )


def downgrade() -> None:
    op.drop_index(
        'ix_ai_reconciliation_suggestions_tenant_id',
        table_name='ai_reconciliation_suggestions'
    )

    op.drop_table('ai_reconciliation_suggestions')
