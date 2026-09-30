from datetime import datetime, UTC

from typing import Optional

import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    get_current_user,
    require_role
)

from app.models.notification import Notification

from app.models.user import User

from app.repositories.client_repository import ClientRepository

from app.services.push_service import PushService


router = APIRouter()


# ============================================================
# SCHEMAS
# ============================================================

class PushDeviceRegisterSchema(BaseModel):

    token: str = Field(min_length=10, max_length=255)

    platform: Optional[str] = None

    device_name: Optional[str] = None


class PushDeviceUnregisterSchema(BaseModel):

    token: str


class NotificationSchema(BaseModel):

    id: uuid.UUID

    tipo: str

    titulo: str

    mensagem: str

    data: Optional[dict] = None

    lida_em: Optional[datetime] = None

    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListSchema(BaseModel):

    nao_lidas: int

    itens: list[NotificationSchema]


class EnviarNotificacaoSchema(BaseModel):
    """Mensagem manual do escritório (ADMIN) pros logins de um cliente."""

    client_id: uuid.UUID

    titulo: str = Field(min_length=1, max_length=120)

    mensagem: str = Field(min_length=1, max_length=1000)


# ============================================================
# APARELHOS (qualquer usuário logado)
# ============================================================

@router.post("/devices")
def register_device(
    data: PushDeviceRegisterSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    PushService.register_device(
        db,
        current_user,
        data.token,
        data.platform,
        data.device_name
    )

    return {"message": "Aparelho registrado"}


@router.post("/devices/unregister")
def unregister_device(
    data: PushDeviceUnregisterSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    PushService.unregister_device(db, current_user, data.token)

    return {"message": "Aparelho removido"}


# ============================================================
# HISTÓRICO (aba "Avisos" do app)
# ============================================================

@router.get("/", response_model=NotificationListSchema)
def list_notifications(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    base = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )

    nao_lidas = base.filter(Notification.lida_em.is_(None)).count()

    itens = (
        base.order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(min(limit, 200))
        .all()
    )

    return {"nao_lidas": nao_lidas, "itens": itens}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    notificacao = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Aviso não encontrado")

    if not notificacao.lida_em:
        notificacao.lida_em = datetime.now(UTC)
        db.commit()

    return {"message": "Aviso marcado como lido"}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.lida_em.is_(None)
        )
        .update(
            {Notification.lida_em: datetime.now(UTC)},
            synchronize_session=False
        )
    )

    db.commit()

    return {"message": "Todos os avisos marcados como lidos"}


# ============================================================
# ENVIO MANUAL (ADMIN -> logins de um cliente da carteira)
# ============================================================

@router.post("/send")
def send_to_client(
    data: EnviarNotificacaoSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    client = ClientRepository.get_by_id(
        db,
        current_user.tenant_id,
        data.client_id
    )

    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    enviados = PushService.notify_client(
        db,
        client.id,
        data.titulo,
        data.mensagem,
        tipo="MENSAGEM",
        data={"screen": "avisos"}
    )

    return {
        "message": "Aviso enviado",
        "push_enviados": enviados
    }
