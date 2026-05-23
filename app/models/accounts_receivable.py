import uuid

from datetime import date

from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    Date,
    Numeric
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class AccountsReceivable(Base):

    __tablename__ = "accounts_receivable"

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

    financial_contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_contacts.id"),
        nullable=False
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_categories.id"),
        nullable=False
    )

    subcategory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_subcategories.id"),
        nullable=True
    )

    descricao: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    valor: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    vencimento: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    data_recebimento: Mapped[date] = mapped_column(
        Date,
        nullable=True
    )

    competencia: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String,
        default="PENDENTE"
    )

    observacao: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")

    financial_contact = relationship(
        "FinancialContact"
    )

    category = relationship(
        "ExpenseCategory"
    )

    subcategory = relationship(
        "ExpenseSubcategory"
    )