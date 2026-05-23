from typing import Optional

from datetime import date

from decimal import Decimal

from pydantic import BaseModel


class BankReconciliationCreateSchema(BaseModel):

    bank_transaction_id: str

    accounts_payable_id: Optional[str] = None

    accounts_receivable_id: Optional[str] = None

    valor_conciliado: Decimal

    data_conciliacao: date

    observacao: Optional[str] = None


class BankReconciliationResponseSchema(BaseModel):

    id: str

    bank_transaction_id: str

    accounts_payable_id: Optional[str]

    accounts_receivable_id: Optional[str]

    valor_conciliado: Decimal

    data_conciliacao: date

    observacao: Optional[str]

    class Config:
        from_attributes = True