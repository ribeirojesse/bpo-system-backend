import uuid

from fastapi import (
    APIRouter,
    Depends,
    Query
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    require_role
)

from app.models.user import User

from app.schemas.accounts_receivable import (
    AccountsReceivableCreateSchema,
    AccountsReceivableUpdateSchema,
    AccountsReceivableResponseSchema
)

from app.services.accounts_receivable_service import (
    AccountsReceivableService
)


router = APIRouter()


# Dado tenant-wide (todos os clients da carteira, não só um). Restrito a
# ADMIN — o portal do CLIENTE (só leitura, escopado a um client) tem suas
# próprias rotas em /portal.


@router.post(
    "/",
    response_model=AccountsReceivableResponseSchema
)
def create_receivable(
    data: AccountsReceivableCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsReceivableService.create_receivable(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[AccountsReceivableResponseSchema]
)
def get_receivables(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=5000),
    client_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsReceivableService.get_receivables(
        db,
        current_user,
        skip,
        limit,
        client_id
    )


@router.get(
    "/{receivable_id}",
    response_model=AccountsReceivableResponseSchema
)
def get_receivable(
    receivable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsReceivableService.get_receivable(
        db,
        current_user,
        receivable_id
    )


@router.put(
    "/{receivable_id}",
    response_model=AccountsReceivableResponseSchema
)
def update_receivable(
    receivable_id: str,
    data: AccountsReceivableUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsReceivableService.update_receivable(
        db,
        current_user,
        receivable_id,
        data
    )


@router.delete("/{receivable_id}")
def delete_receivable(
    receivable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsReceivableService.delete_receivable(
        db,
        current_user,
        receivable_id
    )
