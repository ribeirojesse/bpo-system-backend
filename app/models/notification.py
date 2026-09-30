import uuid

from datetime import datetime

from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    func
)

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.core.database import Base


class Notification(Base):
    """Histórico de notificações de um usuário — é o que o app mostra na
    aba "Avisos" (e o que garante que o aviso não se perde se o push não
    chegar, ex.: celular sem internet ou notificações desligadas)."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Ex.: FECHAMENTO_CONCLUIDO, VENCIMENTO, MENSAGEM
    tipo: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="MENSAGEM"
    )

    titulo: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    mensagem: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    # Dados extras pro app decidir pra qual tela navegar ao tocar
    # (ex.: {"screen": "relatorios"}).
    data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    lida_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
