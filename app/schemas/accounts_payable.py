from typing import Optional

from datetime import date

import uuid

from decimal import Decimal

from pydantic import BaseModel


class AccountsPayableCreateSchema(BaseModel):

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID] = None

    descricao: str

    valor: Decimal

    vencimento: date

    competencia: Optional[str] = None

    observacao: Optional[str] = None


class AccountsPayableUpdateSchema(BaseModel):

    financial_contact_id: Optional[uuid.UUID] = None

    category_id: Optional[uuid.UUID] = None

    subcategory_id: Optional[uuid.UUID] = None

    descricao: Optional[str] = None

    valor: Optional[Decimal] = None

    vencimento: Optional[date] = None

    data_pagamento: Optional[date] = None

    competencia: Optional[str] = None

    status: Optional[str] = None

    observacao: Optional[str] = None


class AccountsPayableResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID]

    descricao: str

    valor: Decimal

    vencimento: date

    data_pagamento: Optional[date]

    competencia: Optional[str]

    status: str

    observacao: Optional[str]

    class Config:
        from_attributes = True