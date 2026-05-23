import uuid

from datetime import date

from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    Date,
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


class BankTransaction(Base):

    __tablename__ = "bank_transactions"

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

    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id"),
        nullable=False
    )

    data_transacao: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    descricao: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    valor: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    tipo: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    documento: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    identificador_externo: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    saldo: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    conciliado: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    processado: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    tenant = relationship("Tenant")

    client = relationship("Client")

    bank_account = relationship(
        "BankAccount"
    )

    hash_transacao: Mapped[str] = mapped_column(
    String,
    nullable=False,
    unique=True
)