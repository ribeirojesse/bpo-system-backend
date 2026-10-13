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

from app.schemas.accounts_payable import (
    AccountsPayableCreateSchema,
    AccountsPayableUpdateSchema,
    AccountsPayableResponseSchema
)

from app.services.accounts_payable_service import (
    AccountsPayableService
)


router = APIRouter()


# Dado tenant-wide (todos os clients da carteira, não só um). Restrito a
# ADMIN — o portal do CLIENTE (só leitura, escopado a um client) tem suas
# próprias rotas em /portal.


@router.post(
    "/",
    response_model=AccountsPayableResponseSchema
)
def create_payable(
    data: AccountsPayableCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsPayableService.create_payable(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[AccountsPayableResponseSchema]
)
def get_payables(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=5000),
    client_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsPayableService.get_payables(
        db,
        current_user,
        skip,
        limit,
        client_id
    )


@router.get(
    "/{payable_id}",
    response_model=AccountsPayableResponseSchema
)
def get_payable(
    payable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsPayableService.get_payable(
        db,
        current_user,
        payable_id
    )


@router.put(
    "/{payable_id}",
    response_model=AccountsPayableResponseSchema
)
def update_payable(
    payable_id: str,
    data: AccountsPayableUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsPayableService.update_payable(
        db,
        current_user,
        payable_id,
        data
    )


@router.delete("/{payable_id}")
def delete_payable(
    payable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return AccountsPayableService.delete_payable(
        db,
        current_user,
        payable_id
    )
