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

from app.schemas.bank_account import (
    BankAccountCreateSchema,
    BankAccountUpdateSchema,
    BankAccountResponseSchema
)

from app.services.bank_account_service import (
    BankAccountService
)


router = APIRouter()


@router.post(
    "/",
    response_model=BankAccountResponseSchema
)
def create_account(
    data: BankAccountCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankAccountService.create_account(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[BankAccountResponseSchema]
)
def get_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankAccountService.get_accounts(
        db,
        current_user
    )


@router.get(
    "/{account_id}",
    response_model=BankAccountResponseSchema
)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankAccountService.get_account(
        db,
        current_user,
        account_id
    )


@router.put(
    "/{account_id}",
    response_model=BankAccountResponseSchema
)
def update_account(
    account_id: str,
    data: BankAccountUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankAccountService.update_account(
        db,
        current_user,
        account_id,
        data
    )


@router.delete("/{account_id}")
def delete_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankAccountService.delete_account(
        db,
        current_user,
        account_id
    )