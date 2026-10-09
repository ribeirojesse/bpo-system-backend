import uuid

from typing import Literal, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    ConfigDict,
    Field
)


TipoContato = Literal["PAGAR", "RECEBER", "AMBOS", "FUNCIONARIO"]


class FinancialContactCreateSchema(BaseModel):

    client_id: uuid.UUID

    nome: str = Field(min_length=1, max_length=200)

    documento: Optional[str] = Field(None, max_length=30)

    email: Optional[EmailStr] = None

    telefone: Optional[str] = Field(None, max_length=30)

    tipo: Optional[TipoContato] = "AMBOS"

    observacao: Optional[str] = Field(None, max_length=2000)


class FinancialContactUpdateSchema(BaseModel):

    nome: Optional[str] = Field(None, min_length=1, max_length=200)

    documento: Optional[str] = Field(None, max_length=30)

    email: Optional[EmailStr] = None

    telefone: Optional[str] = Field(None, max_length=30)

    tipo: Optional[TipoContato] = None

    observacao: Optional[str] = Field(None, max_length=2000)

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