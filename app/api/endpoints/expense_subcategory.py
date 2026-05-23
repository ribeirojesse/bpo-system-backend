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

from app.schemas.expense_subcategory import (
    ExpenseSubcategoryCreateSchema,
    ExpenseSubcategoryResponseSchema
)

from app.services.expense_subcategory_service import (
    ExpenseSubcategoryService
)


router = APIRouter()


@router.post(
    "/",
    response_model=ExpenseSubcategoryResponseSchema
)
def create_subcategory(
    data: ExpenseSubcategoryCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ExpenseSubcategoryService.create_subcategory(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[
        ExpenseSubcategoryResponseSchema
    ]
)
def get_subcategories(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    return (
        ExpenseSubcategoryService.get_subcategories(
            db,
            current_user
        )
    )