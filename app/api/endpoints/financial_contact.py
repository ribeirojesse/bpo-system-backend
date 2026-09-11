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

from app.schemas.financial_contact import (
    FinancialContactCreateSchema,
    FinancialContactUpdateSchema,
    FinancialContactResponseSchema
)

from app.services.financial_contact_service import (
    FinancialContactService
)


router = APIRouter()


@router.post(
    "/",
    response_model=FinancialContactResponseSchema
)
def create_contact(
    data: FinancialContactCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return FinancialContactService.create_contact(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[FinancialContactResponseSchema]
)
def get_contacts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return FinancialContactService.get_contacts(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{contact_id}",
    response_model=FinancialContactResponseSchema
)
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return FinancialContactService.get_contact(
        db,
        current_user,
        contact_id
    )


@router.put(
    "/{contact_id}",
    response_model=FinancialContactResponseSchema
)
def update_contact(
    contact_id: str,
    data: FinancialContactUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return FinancialContactService.update_contact(
        db,
        current_user,
        contact_id,
        data
    )


@router.delete("/{contact_id}")
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return FinancialContactService.delete_contact(
        db,
        current_user,
        contact_id
    )