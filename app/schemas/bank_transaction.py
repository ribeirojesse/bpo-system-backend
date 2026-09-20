from typing import Optional

from datetime import date

from decimal import Decimal

from pydantic import BaseModel

import uuid


class BankTransactionCreateSchema(BaseModel):

    client_id: uuid.UUID

    bank_account_id: uuid.UUID

    data_transacao: date

    descricao: str

    valor: Decimal

    tipo: str

    documento: Optional[str] = None

    identificador_externo: Optional[str] = None

    saldo: Optional[Decimal] = None


class BankTransactionUpdateSchema(BaseModel):

    descricao: Optional[str] = None

    valor: Optional[Decimal] = None

    tipo: Optional[str] = None

    documento: Optional[str] = None

    conciliado: Optional[bool] = None

    saldo: Optional[Decimal] = None


class BankTransactionResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    bank_account_id: uuid.UUID

    data_transacao: date

    descricao: str

    valor: Decimal

    tipo: str

    documento: Optional[str]

    identificador_externo: Optional[str]

    saldo: Optional[Decimal]

    conciliado: bool

    ignorada: bool

    class Config:
        from_attributes = True