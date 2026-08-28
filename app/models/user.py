import uuid

from sqlalchemy import (
    String,
    ForeignKey,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    mapped_column,
    Mapped,
    relationship
)

from app.core.database import Base


class User(Base):

    __tablename__ = "users"

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

    nome: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    senha_hash: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String,
        default="admin"
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship(
        "Tenant"
    )

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )