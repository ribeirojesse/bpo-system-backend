from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    get_current_user,
    require_role
)

from app.models.user import User

from app.schemas.client import (
    ClientCreateSchema,
    ClientUpdateSchema,
    ClientResponseSchema,
    ClientPortalAccessResponseSchema,
    ClientPortalAccessUpdateSchema
)

from app.services.client_service import (
    ClientService
)


router = APIRouter()


# Criar/editar/excluir client é uma ação exclusiva de quem é dono de uma
# carteira (role ADMIN) — é o "USER cria seus próprios clients" do
# desenho de roles. Listar/ver continua liberado pra qualquer usuário
# autenticado (já é filtrado por tenant_id, então não vaza nada).


@router.post(
    "/",
    response_model=ClientResponseSchema
)
def create_client(
    data: ClientCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClientService.create_client(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[ClientResponseSchema]
)
def get_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ClientService.get_clients(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{client_id}",
    response_model=ClientResponseSchema
)
def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ClientService.get_client(
        db,
        current_user,
        client_id
    )


@router.put(
    "/{client_id}",
    response_model=ClientResponseSchema
)
def update_client(
    client_id: str,
    data: ClientUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClientService.update_client(
        db,
        current_user,
        client_id,
        data
    )


@router.delete("/{client_id}")
def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClientService.delete_client(
        db,
        current_user,
        client_id
    )


# ----------------------------------------------------------------------
# Acesso do CLIENTE ao portal. Todo client já nasce com um login CLIENTE
# (criado pela migration b1c4a9d7e2f0 para os que já existiam, e por
# set_portal_access para os novos, se o ADMIN quiser customizar). Aqui o
# ADMIN só consegue ENXERGAR e-mail/trocar credenciais — nunca ver a
# senha atual em texto puro.
# ----------------------------------------------------------------------

@router.get(
    "/{client_id}/portal-access",
    response_model=ClientPortalAccessResponseSchema
)
def get_portal_access(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClientService.get_portal_access(
        db,
        current_user,
        client_id
    )


@router.put(
    "/{client_id}/portal-access",
    response_model=ClientPortalAccessResponseSchema
)
def set_portal_access(
    client_id: str,
    data: ClientPortalAccessUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClientService.set_portal_access(
        db,
        current_user,
        client_id,
        data
    )
