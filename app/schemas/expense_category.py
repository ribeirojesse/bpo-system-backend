from typing import Optional

from uuid import UUID

from pydantic import BaseModel, Field


class ExpenseCategoryCreateSchema(
    BaseModel
):

    client_id: UUID

    nome: str = Field(min_length=1, max_length=200)


class ExpenseCategoryUpdateSchema(
    BaseModel
):

    nome: Optional[str] = Field(None, min_length=1, max_length=200)

    ativo: Optional[bool] = None


class ExpenseCategoryResponseSchema(
    BaseModel
):

    id: UUID

    tenant_id: UUID

    client_id: UUID

    nome: str

    ativo: bool

    class Config:
        from_attributes = True
