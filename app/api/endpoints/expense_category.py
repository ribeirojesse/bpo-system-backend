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

from app.schemas.expense_category import (
    ExpenseCategoryCreateSchema,
    ExpenseCategoryResponseSchema
)

from app.services.expense_category_service import (
    ExpenseCategoryService
)


router = APIRouter()


@router.post(
    "/",
    response_model=ExpenseCategoryResponseSchema
)
def create_category(
    data: ExpenseCategoryCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ExpenseCategoryService.create_category(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[ExpenseCategoryResponseSchema]
)
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ExpenseCategoryService.get_categories(
        db,
        current_user
    )