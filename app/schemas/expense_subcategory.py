from typing import Optional

from uuid import UUID

from pydantic import BaseModel


class ExpenseSubcategoryCreateSchema(
    BaseModel
):

    category_id: UUID

    nome: str


class ExpenseSubcategoryUpdateSchema(
    BaseModel
):

    nome: Optional[str] = None

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
