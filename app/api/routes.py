from fastapi import APIRouter
from app.api.endpoints import (
                                auth,
                                client,
                                financial_contact,
                                expense_category,
                                expense_subcategory,
                                accounts_payable,
                                accounts_receivable,
                                bank_account,
                                bank_transaction,
                                bank_reconciliation,
                                ofx_import,
                                payroll,
                                payroll_batch,
                                admin_user,
                                portal,
                                dre
                              )


api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"]
)

api_router.include_router(
    admin_user.router,
    prefix="/admin/users",
    tags=["Admin - Users"]
)

api_router.include_router(
    client.router,
    prefix="/clients",
    tags=["Clients"]
)

api_router.include_router(
    financial_contact.router,
    prefix="/financial-contacts",
    tags=["Financial Contacts"]
)

api_router.include_router(
    expense_category.router,
    prefix="/expense-categories",
    tags=["Expense Categories"]
)

api_router.include_router(
    expense_subcategory.router,
    prefix="/expense-subcategories",
    tags=["Expense Subcategories"]
)

api_router.include_router(
    accounts_payable.router,
    prefix="/accounts-payable",
    tags=["Accounts Payable"]
)

api_router.include_router(
    accounts_receivable.router,
    prefix="/accounts-receivable",
    tags=["Accounts Receivable"]
)

api_router.include_router(
    bank_account.router,
    prefix="/bank-accounts",
    tags=["Bank Accounts"]
)

api_router.include_router(
    bank_transaction.router,
    prefix="/bank-transactions",
    tags=["Bank Transactions"]
)

api_router.include_router(
    bank_reconciliation.router,
    prefix="/bank-reconciliations",
    tags=["Bank Reconciliations"]
)

api_router.include_router(
    ofx_import.router,
    prefix="/ofx",
    tags=["OFX Import"]
)

# payroll_batch é aninhado dentro do router de payroll para que só
# exista um único include_router com o prefixo "/payroll" (evita
# duplicar a entrada "Payroll" no Swagger/OpenAPI). As URLs finais
# continuam as mesmas: /payroll/process, /payroll/batches,
# /payroll/batch/{id}, /payroll/transaction/{id}.
payroll.router.include_router(payroll_batch.router)

api_router.include_router(
    payroll.router,
    prefix="/payroll",
    tags=["Payroll"]
)

# Portal do CLIENTE — só-leitura, escopado a um único client
# (ver app/api/endpoints/portal.py e app/services/portal_service.py).
api_router.include_router(
    portal.router,
    prefix="/portal",
    tags=["Portal do Cliente"]
)

# Relatório de DRE — disponível pro ADMIN (qualquer cliente da carteira)
# e, escopado ao próprio client_id, pelo CLIENTE no portal (ver
# app/api/endpoints/dre.py e app/services/dre_service.py).
api_router.include_router(
    dre.router,
    prefix="/dre",
    tags=["DRE"]
)
