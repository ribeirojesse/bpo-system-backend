import uuid

from typing import Optional

from sqlalchemy import (
    String,
    ForeignKey,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    mapped_column,
    Mapped,
    relationship
)

from app.core.database import Base


class User(Base):

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Nulo apenas para role = SUPER_ADMIN, que não pertence a nenhum
    # tenant (ver ck_users_role_scope na migration fa3887bfd9e6).
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True
    )

    # Preenchido apenas para role = CLIENTE: restringe o login a UM
    # client específico, em vez de à carteira inteira do tenant.
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=True
    )

    nome: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    senha_hash: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    # Valores válidos: SUPER_ADMIN, ADMIN, CLIENTE.
    # - SUPER_ADMIN: sem tenant_id, sem client_id. Cria os usuários ADMIN
    #   (ver app/api/endpoints/admin_user.py).
    # - ADMIN: sempre com tenant_id, sem client_id. É dono de uma
    #   carteira de clients (o "USER" que cria seus próprios clients).
    # - CLIENTE: sempre com tenant_id E client_id. Login restrito a um
    #   único client (portal do cliente, a ser construído).
    # A combinação é garantida em banco pela constraint
    # ck_users_role_scope (migration fa3887bfd9e6).
    role: Mapped[str] = mapped_column(
        String,
        default="ADMIN"
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    tenant = relationship(
        "Tenant"
    )

    client = relationship(
        "Client"
    )

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
