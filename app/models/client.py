import uuid

from sqlalchemy import (
    String,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class Client(Base):

    __tablename__ = "clients"

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

    razao_social: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    nome_fantasia: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    cnpj: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    telefone: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    tenant = relationship("Tenant")