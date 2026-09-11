from fastapi import HTTPException

from app.repositories.client_repository import (
    ClientRepository
)

from app.repositories.financial_contact_repository import (
    FinancialContactRepository
)

from app.repositories.expense_category_repository import (
    ExpenseCategoryRepository
)

from app.repositories.expense_subcategory_repository import (
    ExpenseSubcategoryRepository
)

from app.repositories.accounts_payable_repository import (
    AccountsPayableRepository
)


class AccountsPayableService:

    @staticmethod
    def create_payable(
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

        contact = FinancialContactRepository.get_by_id(
            db,
            current_user.tenant_id,
            data.financial_contact_id
        )

        if not contact:
            raise HTTPException(
                status_code=404,
                detail="Contato não encontrado"
            )

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

        if data.subcategory_id:

            subcategory = ExpenseSubcategoryRepository.get_by_id(
                db,
                current_user.tenant_id,
                data.subcategory_id
            )

            if not subcategory:
                raise HTTPException(
                    status_code=404,
                    detail="Subcategoria não encontrada"
                )

        payload = data.model_dump()

        payload["tenant_id"] = current_user.tenant_id

        # Regra de negócio: não existe mais "conta pendente aguardando
        # confirmação" nesse sistema. Um lançamento manual representa um
        # pagamento que já aconteceu, então ele já nasce PAGO — sem
        # precisar de uma segunda ação pra "confirmar" o que a pessoa
        # acabou de informar. Se não vier uma data de pagamento explícita,
        # usamos a própria data do lançamento.
        payload["status"] = "PAGO"

        if not payload.get("data_pagamento"):
            payload["data_pagamento"] = payload["vencimento"]

        return AccountsPayableRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_payables(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return AccountsPayableRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

    @staticmethod
    def get_payable(
        db,
        current_user,
        payable_id
    ):

        payable = AccountsPayableRepository.get_by_id(
            db,
            current_user.tenant_id,
            payable_id
        )

        if not payable:
            raise HTTPException(
                status_code=404,
                detail="Conta não encontrada"
            )

        return payable

    @staticmethod
    def update_payable(
        db,
        current_user,
        payable_id,
        data
    ):

        payable = AccountsPayableService.get_payable(
            db,
            current_user,
            payable_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return AccountsPayableRepository.update(
            db,
            payable,
            payload
        )

    @staticmethod
    def delete_payable(
        db,
        current_user,
        payable_id
    ):

        payable = AccountsPayableService.get_payable(
            db,
            current_user,
            payable_id
        )

        AccountsPayableRepository.delete(
            db,
            payable
        )

        return {
            "message": "Conta removida"
        }