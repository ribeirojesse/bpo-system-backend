import uuid

from datetime import date

from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    Numeric,
    Boolean,
    Date
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class CardInvoiceBatch(Base):
    """Uma fatura de cartão de crédito conciliada: guarda o total e a
    conferência com o pagamento que saiu no extrato. Os itens da fatura
    ficam em CardInvoiceItem, cada um com seu lançamento em contas a
    pagar — mesma ideia da folha de pagamento (PayrollBatch)."""

    __tablename__ = "card_invoice_batches"

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

    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_transactions.id"),
        nullable=False
    )

    # Categoria usada nos lançamentos (sempre a "FATURA CARTAO" do
    # cliente, criada na hora se ainda não existir).
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_categories.id"),
        nullable=True
    )

    # Preenchida à mão na tela de conferência (MM/AAAA).
    competencia: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    # Soma dos itens conferidos.
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    # Valor que saiu no extrato (pagamento da fatura).
    valor_transacao: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    # Total declarado na própria fatura, quando o PDF informa.
    valor_total_documento: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    vencimento: Mapped[date] = mapped_column(
        Date,
        nullable=True
    )

    banco: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    conciliado: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    processado: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")

    bank_transaction = relationship("BankTransaction")

    items = relationship(
        "CardInvoiceItem",
        back_populates="batch"
    )
