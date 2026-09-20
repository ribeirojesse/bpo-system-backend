import uuid

from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    Boolean,
    Numeric
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class BankAccount(Base):

    __tablename__ = "bank_accounts"

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

    banco: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    agencia: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    conta: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    tipo_conta: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    saldo_inicial: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")