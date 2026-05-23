from fastapi import HTTPException

from app.repositories.expense_category_repository import (
    ExpenseCategoryRepository
)

from app.repositories.expense_subcategory_repository import (
    ExpenseSubcategoryRepository
)


class ExpenseSubcategoryService:

    @staticmethod
    def create_subcategory(
        db,
        current_user,
        data
    ):

        category = ExpenseCategoryRepository.get_by_id(
                db,
                current_user.tenant_id,
                data.category_id
            )

        if not category:

            raise HTTPException(
                status_code=404,
                detail="Categoria não encontrada"
            )

        payload = data.model_dump()

        return (
            ExpenseSubcategoryRepository.create(
                db,
                payload
            )
        )

    @staticmethod
    def get_subcategories(
        db,
        current_user
    ):

        return (
            ExpenseSubcategoryRepository.get_all(
                db,
                current_user.tenant_id
            )
        )