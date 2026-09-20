import uuid

from sqlalchemy import (
    String,
    ForeignKey,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class FinancialContact(Base):

    __tablename__ = "financial_contacts"

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

    nome: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    documento: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    email: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    telefone: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    tipo: Mapped[str] = mapped_column(
        String,
        default="AMBOS"
    )

    observacao: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")