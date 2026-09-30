from typing import Optional

from datetime import date

from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, Field

import uuid


class BankTransactionCreateSchema(BaseModel):

    client_id: uuid.UUID

    bank_account_id: uuid.UUID

    data_transacao: date

    descricao: str

    valor: Decimal

    tipo: str

    documento: Optional[str] = None

    identificador_externo: Optional[str] = None

    saldo: Optional[Decimal] = None


class BankTransactionUpdateSchema(BaseModel):

    descricao: Optional[str] = None

    valor: Optional[Decimal] = None

    tipo: Optional[str] = None

    documento: Optional[str] = None

    conciliado: Optional[bool] = None

    saldo: Optional[Decimal] = None


class BankTransactionResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    bank_account_id: uuid.UUID

    data_transacao: date

    descricao: str

    valor: Decimal

    tipo: str

    documento: Optional[str]

    identificador_externo: Optional[str]

    saldo: Optional[Decimal]

    conciliado: bool

    # Já era usado pelo frontend (filtro de pendentes, botão "Folha"),
    # mas não vinha na resposta — então nunca era True na tela.
    processado: Optional[bool] = False

    ignorada: bool

    class Config:
        from_attributes = True


class BankTransactionBulkActionSchema(BaseModel):
    """Ação em lote na tela de Conciliação (várias transações selecionadas
    de uma vez)."""

    ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)

    # EXCLUIR: apaga de vez | IGNORAR: arquiva | REABRIR: desarquiva
    acao: Literal["EXCLUIR", "IGNORAR", "REABRIR"]


class BankTransactionBulkRecusadaSchema(BaseModel):

    id: uuid.UUID

    descricao: Optional[str] = None

    motivo: str


class BankTransactionBulkResultSchema(BaseModel):

    acao: str

    processadas: int

    recusadas: list[BankTransactionBulkRecusadaSchema] = []
