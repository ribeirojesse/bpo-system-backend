import uuid

from datetime import datetime

from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    Boolean,
    func
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.core.database import Base


class PushDevice(Base):
    """Aparelho (celular) registrado pra receber push notifications.

    Um mesmo usuário pode ter vários aparelhos; o mesmo token de push só
    pode estar associado a um usuário por vez (se outra pessoa logar no
    mesmo celular, o token é "transferido" — ver PushService.register).
    O token é o "ExponentPushToken[...]" gerado pelo expo-notifications
    no app mobile."""

    __tablename__ = "push_devices"

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

    token: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    # "ios" | "android"
    platform: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    device_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    # Desligado automaticamente quando a Expo responde
    # "DeviceNotRegistered" (app desinstalado / permissão revogada).
    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
