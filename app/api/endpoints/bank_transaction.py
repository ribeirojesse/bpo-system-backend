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

from app.schemas.bank_transaction import (
    BankTransactionCreateSchema,
    BankTransactionUpdateSchema,
    BankTransactionResponseSchema
)

from app.services.bank_transaction_service import (
    BankTransactionService
)


router = APIRouter()


@router.post(
    "/",
    response_model=BankTransactionResponseSchema
)
def create_transaction(
    data: BankTransactionCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankTransactionService.create_transaction(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[BankTransactionResponseSchema]
)
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankTransactionService.get_transactions(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{transaction_id}",
    response_model=BankTransactionResponseSchema
)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankTransactionService.get_transaction(
        db,
        current_user,
        transaction_id
    )


@router.put(
    "/{transaction_id}",
    response_model=BankTransactionResponseSchema
)
def update_transaction(
    transaction_id: str,
    data: BankTransactionUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankTransactionService.update_transaction(
        db,
        current_user,
        transaction_id,
        data
    )


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankTransactionService.delete_transaction(
        db,
        current_user,
        transaction_id
    )


@router.post(
    "/{transaction_id}/ignorar",
    response_model=BankTransactionResponseSchema
)
def ignore_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankTransactionService.ignore_transaction(
        db,
        current_user,
        transaction_id
    )


@router.post(
    "/{transaction_id}/reabrir",
    response_model=BankTransactionResponseSchema
)
def restore_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return BankTransactionService.restore_transaction(
        db,
        current_user,
        transaction_id
    )