from fastapi import HTTPException

from app.repositories.client_repository import (
    ClientRepository
)

from app.repositories.expense_category_repository import (
    ExpenseCategoryRepository
)


class ExpenseCategoryService:

    @staticmethod
    def create_category(
        db,
        current_user,
        data
    ):

        client = ClientRepository.get_by_id(
            db,
            current_user.tenant_id,
            data.client_id
        )

        if not client:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        payload = data.model_dump()

        payload["tenant_id"] = current_user.tenant_id

        return ExpenseCategoryRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_categories(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return ExpenseCategoryRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

    @staticmethod
    def get_category(
        db,
        current_user,
        category_id
    ):

        category = ExpenseCategoryRepository.get_by_id(
            db,
            current_user.tenant_id,
            category_id
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Categoria não encontrada"
            )

        return category

    @staticmethod
    def update_category(
        db,
        current_user,
        category_id,
        data
    ):

        category = ExpenseCategoryService.get_category(
            db,
            current_user,
            category_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return ExpenseCategoryRepository.update(
            db,
            category,
            payload
        )

    @staticmethod
    def delete_category(
        db,
        current_user,
        category_id
    ):

        category = ExpenseCategoryService.get_category(
            db,
            current_user,
            category_id
        )

        ExpenseCategoryRepository.delete(
            db,
            category
        )

        return {
            "message": "Categoria removida"
        }
