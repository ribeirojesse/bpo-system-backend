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

from app.schemas.bank_reconciliation import (
    BankReconciliationCreateSchema,
    BankReconciliationResponseSchema
)

from app.services.bank_reconciliation_service import (
    BankReconciliationService
)


router = APIRouter()


@router.post(
    "/",
    response_model=BankReconciliationResponseSchema
)
def create_reconciliation(
    data: BankReconciliationCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return (
        BankReconciliationService.get_reconciliations(
            db
        )
    )