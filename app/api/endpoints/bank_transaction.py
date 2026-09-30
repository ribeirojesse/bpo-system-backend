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

from app.schemas.bank_transaction import (
    BankTransactionCreateSchema,
    BankTransactionUpdateSchema,
    BankTransactionResponseSchema,
    BankTransactionBulkActionSchema,
    BankTransactionBulkResultSchema
)

from app.services.bank_transaction_service import (
    BankTransactionService
)


router = APIRouter()


# Dado tenant-wide (todos os clients da carteira, não só um). Restrito a
# ADMIN — o portal do CLIENTE (só leitura, escopado a um client) tem suas
# próprias rotas em /portal.


@router.post(
    "/",
    response_model=BankTransactionResponseSchema
)
def create_transaction(
    data: BankTransactionCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
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
    # Padrão continua 100 (compatível), mas as telas pedem mais: com só
    # 100 da carteira inteira, transações ficavam de fora da lista.
    limit: int = Query(100, ge=1, le=20000),
    client_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return BankTransactionService.get_transactions(
        db,
        current_user,
        skip,
        limit,
        client_id
    )


@router.post(
    "/bulk",
    response_model=BankTransactionBulkResultSchema
)
def bulk_action(
    data: BankTransactionBulkActionSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Excluir / ignorar / reabrir várias transações selecionadas."""

    return BankTransactionService.bulk_action(
        db,
        current_user,
        data.ids,
        data.acao
    )


@router.get(
    "/{transaction_id}",
    response_model=BankTransactionResponseSchema
)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
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
    current_user: User = Depends(require_role("ADMIN"))
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
    current_user: User = Depends(require_role("ADMIN"))
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
    current_user: User = Depends(require_role("ADMIN"))
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
    current_user: User = Depends(require_role("ADMIN"))
):

    return BankTransactionService.restore_transaction(
        db,
        current_user,
        transaction_id
    )
