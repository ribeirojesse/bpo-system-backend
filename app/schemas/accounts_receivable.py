from typing import Optional

from datetime import date

from decimal import Decimal

from pydantic import BaseModel

import uuid


class AccountsReceivableCreateSchema(BaseModel):

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID] = None

    descricao: str

    valor: Decimal

    vencimento: date

    competencia: Optional[str] = None

    observacao: Optional[str] = None


class AccountsReceivableUpdateSchema(BaseModel):

    descricao: Optional[str] = None

    valor: Optional[Decimal] = None

    vencimento: Optional[date] = None

    data_recebimento: Optional[date] = None

    competencia: Optional[str] = None

    status: Optional[str] = None

    observacao: Optional[str] = None


class AccountsReceivableResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID]

    descricao: str

    valor: Decimal

    vencimento: date

    data_recebimento: Optional[date]

    competencia: Optional[str]

    status: str

    observacao: Optional[str]

    class Config:
        from_attributes = True