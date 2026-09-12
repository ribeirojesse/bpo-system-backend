from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    require_role
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


# Dado tenant-wide (todos os clients da carteira, não só um). Restrito a
# ADMIN — o portal do CLIENTE (só leitura, escopado a um client) tem sua
# própria rota GET /portal/contas-bancarias.


@router.post(
    "/",
    response_model=BankAccountResponseSchema
)
def create_account(
    data: BankAccountCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
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
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return BankAccountService.get_accounts(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{account_id}",
    response_model=BankAccountResponseSchema
)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
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
    current_user: User = Depends(require_role("ADMIN"))
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
    current_user: User = Depends(require_role("ADMIN"))
):

    return BankAccountService.delete_account(
        db,
        current_user,
        account_id
    )
