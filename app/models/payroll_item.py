import uuid

from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    Numeric
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class PayrollItem(Base):

    __tablename__ = "payroll_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_batches.id"),
        nullable=False
    )

    funcionario: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    cpf: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    valor: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    accounts_payable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts_payable.id"),
        nullable=True
    )

    batch = relationship(
        "PayrollBatch",
        back_populates="items"
    )

    accounts_payable = relationship(
        "AccountsPayable"
    )