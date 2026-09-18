import uuid

from sqlalchemy import (
    String,
    Integer,
    Date,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class ClosingSchedule(Base):

    __tablename__ = "closing_schedules"

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

    # Vínculo opcional a um client específico da carteira — um item de
    # cronograma pode ser genérico (ex: "Fechamento folha geral") ou
    # atrelado a um fechamento pontual de um client.
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=True
    )

    titulo: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    descricao: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    # Competência no formato "MM/YYYY", reaproveitando o mesmo padrão do
    # CompetenciaSelect usado em payable/receivables.
    competencia: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    data_vencimento: Mapped[Date] = mapped_column(
        Date,
        nullable=False
    )

    # Quantos dias antes do vencimento o alerta de lembrete passa a
    # ficar ativo no ícone da aba (ex: 3 = alerta liga 3 dias antes).
    dias_lembrete: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default="3"
    )

    # PENDENTE | CONCLUIDO — "atrasado" não é um status próprio, é
    # calculado (PENDENTE + data_vencimento < hoje), igual ao padrão já
    # usado no resto do sistema para não duplicar estado.
    status: Mapped[str] = mapped_column(
        String,
        default="PENDENTE",
        server_default="PENDENTE"
    )

    data_conclusao: Mapped[Date] = mapped_column(
        Date,
        nullable=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")
