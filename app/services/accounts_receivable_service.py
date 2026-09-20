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

from app.repositories.accounts_receivable_repository import (
    AccountsReceivableRepository
)


class AccountsReceivableService:

    @staticmethod
    def create_receivable(
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
        # recebimento que já aconteceu, então ele já nasce RECEBIDO — sem
        # precisar de uma segunda ação pra "confirmar" o que a pessoa
        # acabou de informar. Se não vier uma data de recebimento
        # explícita, usamos a própria data do lançamento.
        payload["status"] = "RECEBIDO"

        if not payload.get("data_recebimento"):
            payload["data_recebimento"] = payload["vencimento"]

        return AccountsReceivableRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_receivables(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        return AccountsReceivableRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

    @staticmethod
    def get_receivable(
        db,
        current_user,
        receivable_id
    ):

        receivable = AccountsReceivableRepository.get_by_id(
            db,
            current_user.tenant_id,
            receivable_id
        )

        if not receivable:
            raise HTTPException(
                status_code=404,
                detail="Conta não encontrada"
            )

        return receivable

    @staticmethod
    def update_receivable(
        db,
        current_user,
        receivable_id,
        data
    ):

        receivable = AccountsReceivableService.get_receivable(
            db,
            current_user,
            receivable_id
        )

        payload = data.model_dump(
            exclude_unset=True
        )

        return AccountsReceivableRepository.update(
            db,
            receivable,
            payload
        )

    @staticmethod
    def delete_receivable(
        db,
        current_user,
        receivable_id
    ):

        receivable = AccountsReceivableService.get_receivable(
            db,
            current_user,
            receivable_id
        )

        AccountsReceivableRepository.delete(
            db,
            receivable
        )

        return {
            "message": "Conta removida"
        }