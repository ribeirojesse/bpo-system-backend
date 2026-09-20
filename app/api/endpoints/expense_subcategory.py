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

from app.schemas.expense_subcategory import (
    ExpenseSubcategoryCreateSchema,
    ExpenseSubcategoryUpdateSchema,
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
    current_user: User = Depends(require_role("ADMIN"))
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
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN")
    )
):

    return (
        ExpenseSubcategoryService.get_subcategories(
            db,
            current_user,
            skip,
            limit
        )
    )


@router.get(
    "/{subcategory_id}",
    response_model=ExpenseSubcategoryResponseSchema
)
def get_subcategory(
    subcategory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ExpenseSubcategoryService.get_subcategory(
        db,
        current_user,
        subcategory_id
    )


@router.put(
    "/{subcategory_id}",
    response_model=ExpenseSubcategoryResponseSchema
)
def update_subcategory(
    subcategory_id: str,
    data: ExpenseSubcategoryUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ExpenseSubcategoryService.update_subcategory(
        db,
        current_user,
        subcategory_id,
        data
    )


@router.delete("/{subcategory_id}")
def delete_subcategory(
    subcategory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ExpenseSubcategoryService.delete_subcategory(
        db,
        current_user,
        subcategory_id
    )
