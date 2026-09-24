from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.core.database import Base

# IMPORTAR MODELS
from app.models.tenant import Tenant
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.client import Client
from app.models.financial_contact import FinancialContact
from app.models.expense_category import ExpenseCategory
from app.models.expense_subcategory import ExpenseSubcategory
from app.models.accounts_payable import AccountsPayable
from app.models.accounts_receivable import AccountsReceivable
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.bank_reconciliation import BankReconciliation
from app.models.payroll_item import PayrollItem
from app.models.payroll_batch import PayrollBatch
from app.models.ai_reconciliation_suggestion import AIReconciliationSuggestion


config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()