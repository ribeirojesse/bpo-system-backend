import uuid

from sqlalchemy import (
    String,
    ForeignKey,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.core.database import Base


class DreTemplate(Base):
    """Modelo salvo de configuração de DRE (Demonstração de Resultado):
    quais categorias entram no relatório, em que ordem, agrupadas em
    quais blocos (linhas com nome próprio, ex.: "Custos com Pessoal" =
    Folha + Encargos), e com qual cor de destaque no PDF. Reaproveitável
    entre gerações do mesmo relatório, tanto pelo ADMIN quanto pelo
    próprio cliente no portal (ver app/services/dre_service.py).

    client_id nulo = modelo "padrão da carteira" (o ADMIN organiza um
    modelo reutilizável entre vários clientes do tenant); client_id
    preenchido = modelo específico daquele cliente — é o único tipo que
    o portal do CLIENTE pode criar."""

    __tablename__ = "dre_templates"

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
        nullable=True
    )

    nome: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    # "CATEGORIA", "BANCO" ou "BANCO_CATEGORIA" — ver DreService.gerar.
    modo: Mapped[str] = mapped_column(
        String,
        default="CATEGORIA"
    )

    cor_destaque: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    # {"blocos": [{"nome": str, "tipo": "RECEITA"|"DESPESA",
    # "category_ids": [uuid,...], "ordem": int}, ...]} — guardado como
    # JSON pra não precisar de mais tabelas relacionais só pra isso; a
    # lista inteira é sempre lida/escrita de uma vez, nunca filtrada por
    # dentro do JSON em SQL.
    config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship("Tenant")

    client = relationship("Client")
