from uuid import UUID

from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr
)


class ClientCreateSchema(BaseModel):

    razao_social: str
    nome_fantasia: Optional[str] = None
    cnpj: str

    email: Optional[EmailStr] = None
    telefone: Optional[str] = None


class ClientUpdateSchema(BaseModel):

    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None

    email: Optional[EmailStr] = None
    telefone: Optional[str] = None


class ClientResponseSchema(BaseModel):

    id: UUID

    razao_social: str
    nome_fantasia: Optional[str]
    cnpj: str

    email: Optional[str]
    telefone: Optional[str]

    class Config:
        from_attributes = True