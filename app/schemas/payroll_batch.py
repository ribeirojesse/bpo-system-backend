from datetime import date

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

    client_id: uuid.UUID

    bank_transaction_id: uuid.UUID

    competencia: str

    valor_total: Decimal

    valor_transacao: Decimal

    conciliado: bool

    # Conta bancária de onde a folha saiu e a data do débito, vindas da
    # transação do extrato que originou o lote (preenchidas no serviço).
    conta_nome: str | None = None

    data_transacao: date | None = None

    items: list[
        PayrollItemResponseSchema
    ]

    class Config:

        from_attributes = True