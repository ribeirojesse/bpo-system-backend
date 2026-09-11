from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    get_current_user
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


@router.post(
    "/",
    response_model=AccountsReceivableResponseSchema
)
def create_receivable(
    data: AccountsReceivableCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return AccountsReceivableService.get_receivables(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{receivable_id}",
    response_model=AccountsReceivableResponseSchema
)
def get_receivable(
    receivable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):

    return AccountsReceivableService.delete_receivable(
        db,
        current_user,
        receivable_id
    )