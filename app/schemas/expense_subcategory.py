from typing import Optional

from uuid import UUID

from pydantic import BaseModel, Field


class ExpenseSubcategoryCreateSchema(
    BaseModel
):

    category_id: UUID

    nome: str = Field(min_length=1, max_length=200)


class ExpenseSubcategoryUpdateSchema(
    BaseModel
):

    nome: Optional[str] = Field(None, min_length=1, max_length=200)

    ativo: Optional[bool] = None


class ExpenseSubcategoryResponseSchema(
    BaseModel
):

    id: UUID

    category_id: UUID

    nome: str

    ativo: bool

    class Config:
        from_attributes = True
