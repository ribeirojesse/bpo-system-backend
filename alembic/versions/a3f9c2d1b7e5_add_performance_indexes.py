"""add performance indexes (client/date filters, reconciliation joins)

Revision ID: a3f9c2d1b7e5
Revises: f1d2c3b4a5e6
Create Date: 2026-10-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a3f9c2d1b7e5'
down_revision: Union[str, Sequence[str], None] = 'f1d2c3b4a5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# O Postgres não cria índice automático para chaves estrangeiras, e as
# telas de Conciliação / Contas a Pagar / Contas a Receber filtram por
# tenant + cliente (+ data) e fazem JOIN pela conciliação. IF NOT EXISTS
# deixa a migration segura caso algum índice já tenha sido criado à mão.
INDICES = [
    ("ix_accounts_payable_tenant_client_venc",
     "accounts_payable", "tenant_id, client_id, vencimento"),

    ("ix_accounts_receivable_tenant_client_venc",
     "accounts_receivable", "tenant_id, client_id, vencimento"),

    ("ix_bank_transactions_tenant_client_data",
     "bank_transactions", "tenant_id, client_id, data_transacao"),

    ("ix_bank_transactions_bank_account",
     "bank_transactions", "bank_account_id"),

    ("ix_bank_reconciliations_tenant_data",
     "bank_reconciliations", "tenant_id, data_conciliacao"),

    ("ix_bank_reconciliations_transaction",
     "bank_reconciliations", "bank_transaction_id"),

    ("ix_bank_reconciliations_payable",
     "bank_reconciliations", "accounts_payable_id"),

    ("ix_bank_reconciliations_receivable",
     "bank_reconciliations", "accounts_receivable_id"),

    ("ix_financial_contacts_tenant_client",
     "financial_contacts", "tenant_id, client_id"),
]


def upgrade():

    for nome, tabela, colunas in INDICES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {nome} "
            f"ON {tabela} ({colunas})"
        )


def downgrade():

    for nome, _tabela, _colunas in reversed(INDICES):
        op.execute(f"DROP INDEX IF EXISTS {nome}")
