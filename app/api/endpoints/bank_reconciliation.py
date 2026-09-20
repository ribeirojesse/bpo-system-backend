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

from app.schemas.bank_reconciliation import (
    BankReconciliationCreateSchema,
    BankReconciliationFromTransactionSchema,
    BankReconciliationResponseSchema,
    ReconciliationSuggestionSchema
)

from app.services.bank_reconciliation_service import (
    BankReconciliationService
)


router = APIRouter()


# Dado tenant-wide (todos os clients da carteira, não só um). Restrito a
# ADMIN — o CLIENTE não opera conciliação, só vê o resultado dela nos
# lançamentos do portal (/portal/lancamentos).


@router.post(
    "/from-transaction/{transaction_id}",
    response_model=BankReconciliationResponseSchema
)
def create_reconciliation_from_transaction(
    transaction_id: str,
    data: BankReconciliationFromTransactionSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Fluxo padrão da tela de Conciliação: cria o lançamento
    (conta a pagar/receber, já PAGO/RECEBIDO) e concilia a transação
    bancária em uma única operação atômica."""

    return (
        BankReconciliationService
        .create_reconciliation_from_transaction(
            db,
            current_user,
            transaction_id,
            data
        )
    )


@router.post(
    "/",
    response_model=BankReconciliationResponseSchema
)
def create_reconciliation(
    data: BankReconciliationCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return (
        BankReconciliationService.create_reconciliation(
            db,
            current_user,
            data
        )
    )


@router.get(
    "/",
    response_model=list[
        BankReconciliationResponseSchema
    ]
)
def get_reconciliations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return (
        BankReconciliationService.get_reconciliations(
            db,
            current_user,
            skip,
            limit
        )
    )


@router.get(
    "/suggestions",
    response_model=list[
        ReconciliationSuggestionSchema
    ]
)
def get_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Sugestão de lançamento existente pra cada transação bancária
    pendente — a base da tela de Conciliação no estilo Conta Azul.
    Precisa vir antes de '/{reconciliation_id}' na definição das rotas,
    senão o FastAPI tentaria tratar 'suggestions' como um UUID."""

    return (
        BankReconciliationService.get_suggestions(
            db,
            current_user
        )
    )


@router.get(
    "/{reconciliation_id}",
    response_model=BankReconciliationResponseSchema
)
def get_reconciliation(
    reconciliation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return (
        BankReconciliationService.get_reconciliation(
            db,
            current_user,
            reconciliation_id
        )
    )


@router.delete("/{reconciliation_id}")
def delete_reconciliation(
    reconciliation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return (
        BankReconciliationService.delete_reconciliation(
            db,
            current_user,
            reconciliation_id
        )
    )
