import uuid

from datetime import datetime

from sqlalchemy import String, DateTime, func

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Lead(Base):
    """Contato vindo do formulário "Agendar diagnóstico" do site
    (landing page). Não pertence a tenant nenhum: é o comercial da própria
    Tower, visível só pra ADMIN e SUPER_ADMIN (ver api/endpoints/lead.py).

    É salvo ANTES de o visitante ser levado ao WhatsApp — se ele desistir
    no meio do caminho, o contato não se perde. Os parâmetros de origem
    (utm_*, gclid, fbclid...) permitem saber de qual anúncio veio cada
    lead e, se quiser, importar a conversão offline no Google Ads."""

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    nome: Mapped[str] = mapped_column(String(120), nullable=False)

    empresa: Mapped[str] = mapped_column(String(160), nullable=False)

    # Só dígitos, com DDD (ex.: 42999990000).
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False)

    volume: Mapped[str | None] = mapped_column(String(40), nullable=True)

    mensagem: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Página do site em que o formulário foi enviado (ex.: "/").
    pagina: Mapped[str | None] = mapped_column(String(200), nullable=True)

    utm_source: Mapped[str | None] = mapped_column(String(200), nullable=True)

    utm_medium: Mapped[str | None] = mapped_column(String(200), nullable=True)

    utm_campaign: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Todos os parâmetros de origem capturados (utm_term, utm_content,
    # gclid, gbraid, wbraid, fbclid...).
    atribuicao: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # NOVO, EM_CONTATO, CONVERTIDO ou DESCARTADO
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NOVO",
        server_default="NOVO"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
