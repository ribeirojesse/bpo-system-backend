from uuid import UUID

from pydantic import BaseModel


class ExpenseCategoryCreateSchema(
    BaseModel
):

    client_id: UUID

    nome: str


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