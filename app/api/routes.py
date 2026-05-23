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
                                payroll_batch
                              )


api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"]
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

api_router.include_router(
    payroll.router,
    prefix="/payroll",
    tags=["Payroll"]
)

api_router.include_router(
    payroll_batch.router,
    prefix="/payroll",
    tags=["Payroll"]
)