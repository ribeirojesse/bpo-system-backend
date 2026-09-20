import uuid

from decimal import Decimal

from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict
)


class BankAccountCreateSchema(BaseModel):

    client_id: uuid.UUID

    banco: str

    agencia: Optional[str] = None

    conta: str

    tipo_conta: Optional[str] = None

    saldo_inicial: Decimal = 0

    ativo: bool = True


class BankAccountUpdateSchema(BaseModel):

    banco: Optional[str] = None

    agencia: Optional[str] = None

    conta: Optional[str] = None

    tipo_conta: Optional[str] = None

    saldo_inicial: Optional[Decimal] = None

    ativo: Optional[bool] = None


class BankAccountResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    banco: str

    agencia: Optional[str] = None

    conta: str

    tipo_conta: Optional[str] = None

    saldo_inicial: Decimal

    ativo: bool

    model_config = ConfigDict(
        from_attributes=True
    )