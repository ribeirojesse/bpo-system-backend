from decimal import Decimal

from pydantic import BaseModel

import uuid


class PayrollItemResponseSchema(
    BaseModel
):

    id: uuid.UUID

    funcionario: str

    cpf: str | None

    valor: Decimal

    accounts_payable_id: uuid.UUID | None

    class Config:

        from_attributes = True     


class PayrollBatchResponseSchema(
    BaseModel
):

    id: uuid.UUID

    competencia: str

    valor_total: Decimal

    valor_transacao: Decimal

    conciliado: bool

    items: list[
        PayrollItemResponseSchema
    ]

    class Config:

        from_attributes = True