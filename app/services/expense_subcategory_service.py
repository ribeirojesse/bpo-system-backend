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
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return (
            ExpenseSubcategoryRepository.get_all(
                db,
                current_user.tenant_id,
                skip,
                limit
            )
        )

    @staticmethod
    def get_subcategory(
        db,
        current_user,
        subcategory_id
    ):

        subcategory = (
            ExpenseSubcategoryRepository.get_by_id(
                db,
                current_user.tenant_id,
                subcategory_id
            )
        )

        if not subcategory:
            raise HTTPException(
                status_code=404,
                detail="Subcategoria não encontrada"
            )

        return subcategory

    @staticmethod
    def update_subcategory(
        db,
        current_user,
        subcategory_id,
        data
    ):

        subcategory = ExpenseSubcategoryService.get_subcategory(
            db,
            current_user,
            subcategory_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return ExpenseSubcategoryRepository.update(
            db,
            subcategory,
            payload
        )

    @staticmethod
    def delete_subcategory(
        db,
        current_user,
        subcategory_id
    ):

        subcategory = ExpenseSubcategoryService.get_subcategory(
            db,
            current_user,
            subcategory_id
        )

        ExpenseSubcategoryRepository.delete(
            db,
            subcategory
        )

        return {
            "message": "Subcategoria removida"
        }
