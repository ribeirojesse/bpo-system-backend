"""create card invoice tables (conciliação de fatura de cartão)

Revision ID: b7e4d1a9c3f2
Revises: a3f9c2d1b7e5
Create Date: 2026-10-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b7e4d1a9c3f2'
down_revision: Union[str, Sequence[str], None] = 'a3f9c2d1b7e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.create_table(
        'card_invoice_batches',

        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True
        ),

        sa.Column(
            'tenant_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('tenants.id'),
            nullable=False
        ),

        sa.Column(
            'client_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('clients.id'),
            nullable=False
        ),

        sa.Column(
            'bank_transaction_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('bank_transactions.id'),
            nullable=False
        ),

        sa.Column(
            'category_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('expense_categories.id'),
            nullable=True
        ),

        sa.Column('competencia', sa.String(), nullable=False),

        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),

        sa.Column('valor_transacao', sa.Numeric(10, 2), nullable=False),

        sa.Column(
            'valor_total_documento',
            sa.Numeric(10, 2),
            nullable=True
        ),

        sa.Column('vencimento', sa.Date(), nullable=True),

        sa.Column('banco', sa.String(), nullable=True),

        sa.Column(
            'conciliado',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        ),

        sa.Column(
            'processado',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true')
        ),
    )

    # Uma transação do extrato só pode ter uma fatura processada.
    op.create_index(
        'ix_card_invoice_batches_transaction',
        'card_invoice_batches',
        ['bank_transaction_id'],
        unique=True
    )

    op.create_index(
        'ix_card_invoice_batches_tenant_client',
        'card_invoice_batches',
        ['tenant_id', 'client_id']
    )

    op.create_table(
        'card_invoice_items',

        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True
        ),

        sa.Column(
            'batch_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('card_invoice_batches.id'),
            nullable=False
        ),

        sa.Column('data_compra', sa.Date(), nullable=True),

        sa.Column('descricao', sa.String(), nullable=False),

        sa.Column('valor', sa.Numeric(10, 2), nullable=False),

        sa.Column('parcela', sa.String(), nullable=True),

        sa.Column('cartao', sa.String(), nullable=True),

        sa.Column(
            'accounts_payable_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('accounts_payable.id'),
            nullable=True
        ),
    )

    op.create_index(
        'ix_card_invoice_items_batch',
        'card_invoice_items',
        ['batch_id']
    )


def downgrade():

    op.drop_index('ix_card_invoice_items_batch', 'card_invoice_items')

    op.drop_table('card_invoice_items')

    op.drop_index(
        'ix_card_invoice_batches_tenant_client',
        'card_invoice_batches'
    )

    op.drop_index(
        'ix_card_invoice_batches_transaction',
        'card_invoice_batches'
    )

    op.drop_table('card_invoice_batches')
