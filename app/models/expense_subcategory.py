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


class ExpenseSubcategory(Base):

    __tablename__ = "expense_subcategories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_categories.id"),
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

    category = relationship(
        "ExpenseCategory",
        back_populates="subcategories"
    )