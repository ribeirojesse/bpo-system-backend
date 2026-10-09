import uuid

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.rate_limit import rate_limit

from app.dependencies.auth import require_role

from app.models.lead import Lead

from app.models.user import User

from app.schemas.lead import (
    LeadCreateSchema,
    LeadResponseSchema,
    LeadStatusUpdateSchema
)


router = APIRouter()


# ------------------------------------------------------------------
# PÚBLICO — formulário do site (landing page)
# ------------------------------------------------------------------
# Sem login, então com limite por IP bem mais apertado que o resto da
# API (o nginx ainda tem o limite geral por cima) e um honeypot contra
# robôs (ver LeadCreateSchema.website).

@router.post(
    "/public",
    status_code=201,
    dependencies=[
        Depends(rate_limit("lead", 5, 600)),
        Depends(rate_limit("lead-dia", 20, 86400)),
    ]
)
def create_public_lead(
    data: LeadCreateSchema,
    db: Session = Depends(get_db)
):

    if data.website:
        return {"ok": True}

    atribuicao = data.atribuicao or {}

    lead = Lead(
        nome=data.nome,
        empresa=data.empresa,
        whatsapp=data.whatsapp,
        volume=(data.volume or None),
        mensagem=(data.mensagem or "").strip() or None,
        pagina=data.pagina,
        utm_source=atribuicao.get("utm_source"),
        utm_medium=atribuicao.get("utm_medium"),
        utm_campaign=atribuicao.get("utm_campaign"),
        atribuicao=atribuicao or None,
    )

    db.add(lead)
    db.commit()

    return {"ok": True}


# ------------------------------------------------------------------
# INTERNO — tela "Leads do site" (ADMIN e SUPER_ADMIN)
# ------------------------------------------------------------------

@router.get(
    "",
    response_model=list[LeadResponseSchema]
)
def list_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "SUPER_ADMIN"))
):

    return (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .limit(500)
        .all()
    )


@router.patch(
    "/{lead_id}",
    response_model=LeadResponseSchema
)
def update_lead_status(
    lead_id: uuid.UUID,
    data: LeadStatusUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "SUPER_ADMIN"))
):

    lead = db.get(Lead, lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead.status = data.status

    db.commit()
    db.refresh(lead)

    return lead
