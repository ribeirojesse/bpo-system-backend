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


class ExpenseCategory(Base):

    __tablename__ = "expense_categories"

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

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")

    subcategories = relationship(
        "ExpenseSubcategory",
        back_populates="category"
    )