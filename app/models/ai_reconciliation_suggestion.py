import uuid

from datetime import datetime

from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    func
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.core.database import Base


class AIReconciliationSuggestion(Base):
    """Sugestão da IA para uma transação bancária pendente. Guardada pra
    não chamar a IA de novo toda vez que a tela de Conciliação abre (custo
    e tempo). Nunca concilia nada sozinha: é só o que aparece pré-
    preenchido pro usuário confirmar com um clique.

    Todos os IDs aqui já foram validados contra o tenant/cliente da
    transação no momento em que a sugestão foi gravada."""

    __tablename__ = "ai_reconciliation_suggestions"

    __table_args__ = (
        UniqueConstraint(
            "bank_transaction_id",
            name="uq_ai_reconciliation_suggestions_transaction"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False
    )

    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_transactions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Lançamento existente sugerido pra vincular ("PAYABLE"/"RECEIVABLE").
    tipo_match: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Pra quando não há lançamento pra vincular: o que pré-preencher no
    # "Criar lançamento".
    financial_contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_contacts.id", ondelete="SET NULL"),
        nullable=True
    )

    novo_fornecedor_nome: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True
    )

    subcategory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_subcategories.id", ondelete="SET NULL"),
        nullable=True
    )

    competencia: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    # "ALTA" / "MEDIA" / "BAIXA"
    confianca: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    justificativa: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    modelo: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
