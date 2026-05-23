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
        current_user
    ):

        return ExpenseCategoryRepository.get_all(
            db,
            current_user.tenant_id
        )