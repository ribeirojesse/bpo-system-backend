import uuid

from datetime import date

from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Date,
    Numeric,
    String
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class BankReconciliation(Base):

    __tablename__ = "bank_reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False
    )

    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_transactions.id"),
        nullable=False
    )

    accounts_payable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts_payable.id"),
        nullable=True
    )

    accounts_receivable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts_receivable.id"),
        nullable=True
    )

    valor_conciliado: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    data_conciliacao: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    observacao: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    tenant = relationship(
        "Tenant"
    )

    bank_transaction = relationship(
        "BankTransaction"
    )

    accounts_payable = relationship(
        "AccountsPayable"
    )

    accounts_receivable = relationship(
        "AccountsReceivable"
    )