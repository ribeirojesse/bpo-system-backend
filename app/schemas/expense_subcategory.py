from uuid import UUID

from pydantic import BaseModel


class ExpenseSubcategoryCreateSchema(
    BaseModel
):

    category_id: UUID

    nome: str


class ExpenseSubcategoryResponseSchema(
    BaseModel
):

    id: UUID

    category_id: UUID

    nome: str

    ativo: bool

    class Config:
        from_attributes = True