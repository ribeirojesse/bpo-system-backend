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

from app.schemas.accounts_payable import (
    AccountsPayableCreateSchema,
    AccountsPayableUpdateSchema,
    AccountsPayableResponseSchema
)

from app.services.accounts_payable_service import (
    AccountsPayableService
)


router = APIRouter()


@router.post(
    "/",
    response_model=AccountsPayableResponseSchema
)
def create_payable(
    data: AccountsPayableCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return AccountsPayableService.get_payables(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{payable_id}",
    response_model=AccountsPayableResponseSchema
)
def get_payable(
    payable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):

    return AccountsPayableService.delete_payable(
        db,
        current_user,
        payable_id
    )