import uuid

from datetime import date

from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    Numeric,
    Date
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class CardInvoiceItem(Base):
    """Uma linha da fatura (compra, estorno, encargo). Valor negativo =
    crédito na fatura (estorno, pagamento, desconto)."""

    __tablename__ = "card_invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("card_invoice_batches.id"),
        nullable=False
    )

    data_compra: Mapped[date] = mapped_column(
        Date,
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

    # "03/10" quando a fatura mostra compra parcelada.
    parcela: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    # Final do cartão ou nome do portador, quando a fatura separa.
    cartao: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    accounts_payable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts_payable.id"),
        nullable=True
    )

    batch = relationship(
        "CardInvoiceBatch",
        back_populates="items"
    )

    accounts_payable = relationship("AccountsPayable")
