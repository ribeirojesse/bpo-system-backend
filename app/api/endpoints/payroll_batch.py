from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.database import (
    get_db
)

from app.dependencies.auth import (
    get_current_user
)

from app.models.user import User

from app.schemas.payroll_batch import (
    PayrollBatchResponseSchema
)

from app.services.payroll_batch_service import (
    PayrollBatchService
)


router = APIRouter()


@router.get(
    "/batches",
    response_model=list[
        PayrollBatchResponseSchema
    ]
)
def get_batches(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    return (
        PayrollBatchService.get_batches(
            db,
            current_user,
            skip,
            limit
        )
    )


@router.get(
    "/batch/{batch_id}",
    response_model=
    PayrollBatchResponseSchema
)
def get_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    return (
        PayrollBatchService.get_batch(
            db,
            current_user,
            batch_id
        )
    )

@router.get("/transaction/{transaction_id}")
def get_batch_by_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return PayrollBatchService.get_by_transaction(
        db,
        current_user,
        transaction_id
    )
