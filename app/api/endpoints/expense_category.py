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

from app.schemas.expense_category import (
    ExpenseCategoryCreateSchema,
    ExpenseCategoryUpdateSchema,
    ExpenseCategoryResponseSchema
)

from app.services.expense_category_service import (
    ExpenseCategoryService
)


router = APIRouter()


# Dado tenant-wide (todos os clients da carteira, não só um). Restrito a
# ADMIN — o portal do CLIENTE (só leitura, escopado a um client) tem sua
# própria rota GET /portal/categorias.


@router.post(
    "/",
    response_model=ExpenseCategoryResponseSchema
)
def create_category(
    data: ExpenseCategoryCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
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
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ExpenseCategoryService.get_categories(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{category_id}",
    response_model=ExpenseCategoryResponseSchema
)
def get_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ExpenseCategoryService.get_category(
        db,
        current_user,
        category_id
    )


@router.put(
    "/{category_id}",
    response_model=ExpenseCategoryResponseSchema
)
def update_category(
    category_id: str,
    data: ExpenseCategoryUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ExpenseCategoryService.update_category(
        db,
        current_user,
        category_id,
        data
    )


@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ExpenseCategoryService.delete_category(
        db,
        current_user,
        category_id
    )
