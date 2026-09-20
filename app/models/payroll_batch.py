import uuid

from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    Numeric,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class PayrollBatch(Base):

    __tablename__ = "payroll_batches"

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

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False
    )

    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_transactions.id"),
        nullable=False
    )

    competencia: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    valor_transacao: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    conciliado: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    processado: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")

    bank_transaction = relationship(
        "BankTransaction"
    )

    items = relationship(
        "PayrollItem",
        back_populates="batch"
    )