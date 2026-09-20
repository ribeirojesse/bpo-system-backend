import uuid

from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    ConfigDict
)


class FinancialContactCreateSchema(BaseModel):

    client_id: uuid.UUID

    nome: str

    documento: Optional[str] = None

    email: Optional[EmailStr] = None

    telefone: Optional[str] = None

    tipo: Optional[str] = "AMBOS"

    observacao: Optional[str] = None


class FinancialContactUpdateSchema(BaseModel):

    nome: Optional[str] = None

    documento: Optional[str] = None

    email: Optional[EmailStr] = None

    telefone: Optional[str] = None

    tipo: Optional[str] = None

    observacao: Optional[str] = None

    ativo: Optional[bool] = None


class FinancialContactResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    nome: str

    documento: Optional[str] = None

    email: Optional[str] = None

    telefone: Optional[str] = None

    tipo: str

    observacao: Optional[str] = None

    ativo: bool

    model_config = ConfigDict(
        from_attributes=True
    )