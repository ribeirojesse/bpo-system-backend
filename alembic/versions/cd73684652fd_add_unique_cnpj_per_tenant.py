"""add unique cnpj per tenant

Revision ID: cd73684652fd
Revises: 841e94f0a0a5
Create Date: 2026-09-09 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cd73684652fd'
down_revision: Union[str, Sequence[str], None] = '841e94f0a0a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ATENÇÃO: se já existirem clientes com CNPJ duplicado para o
    # mesmo tenant, esta migration falha. Antes de rodar em um banco
    # com dados reais, verifique com:
    #
    #   SELECT tenant_id, cnpj, COUNT(*)
    #   FROM clients
    #   GROUP BY tenant_id, cnpj
    #   HAVING COUNT(*) > 1;
    #
    # e resolva as duplicatas antes de aplicar esta migration.
    op.create_unique_constraint(
        'uq_clients_tenant_cnpj',
        'clients',
        ['tenant_id', 'cnpj']
    )


def downgrade():
    op.drop_constraint(
        'uq_clients_tenant_cnpj',
        'clients',
        type_='unique'
    )
