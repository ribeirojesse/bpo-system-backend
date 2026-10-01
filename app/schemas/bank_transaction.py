from typing import Optional

from datetime import date

from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, Field, field_validator

import uuid


# Mesmo padrão da importação de OFX (ofx_import_service.py): tipo é
# CREDITO (entrou na conta) ou DEBITO (saiu) e o valor é sempre
# positivo. A Conciliação decide "recebimento x pagamento" por
# tipo == "CREDITO" — por isso o formulário antigo, que mandava
# ENTRADA/SAIDA, fazia uma entrada manual aparecer como pagamento.
TIPOS_ALIAS = {
    "CREDITO": "CREDITO",
    "CRÉDITO": "CREDITO",
    "ENTRADA": "CREDITO",
    "DEBITO": "DEBITO",
    "DÉBITO": "DEBITO",
    "SAIDA": "DEBITO",
    "SAÍDA": "DEBITO",
}


def _normalizar_tipo(value):

    if value is None:
        return value

    tipo = TIPOS_ALIAS.get(str(value).strip().upper())

    if not tipo:
        raise ValueError("Tipo deve ser CREDITO (entrada) ou DEBITO (saída)")

    return tipo


def _vazio_para_none(value):

    if isinstance(value, str) and not value.strip():
        return None

    return value


class BankTransactionCreateSchema(BaseModel):

    client_id: uuid.UUID

    bank_account_id: uuid.UUID

    data_transacao: date

    descricao: str = Field(min_length=1, max_length=500)

    valor: Decimal = Field(gt=0)

    tipo: Literal["CREDITO", "DEBITO"]

    documento: Optional[str] = None

    identificador_externo: Optional[str] = None

    saldo: Optional[Decimal] = None

    @field_validator("tipo", mode="before")
    @classmethod
    def validar_tipo(cls, value):
        return _normalizar_tipo(value)

    @field_validator("documento", "identificador_externo", "saldo", mode="before")
    @classmethod
    def limpar_vazios(cls, value):
        return _vazio_para_none(value)

    @field_validator("valor", mode="before")
    @classmethod
    def valor_positivo(cls, value):
        # Aceita "-150,00" vindo de quem copia do extrato: o sinal fica
        # no tipo, o valor é sempre positivo.
        value = _vazio_para_none(value)
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", ".") \
                if "," in value else value
        return abs(Decimal(str(value))) if value is not None else value

    @field_validator("descricao", mode="before")
    @classmethod
    def limpar_descricao(cls, value):
        return value.strip() if isinstance(value, str) else value


class BankTransactionUpdateSchema(BaseModel):

    bank_account_id: Optional[uuid.UUID] = None

    data_transacao: Optional[date] = None

    descricao: Optional[str] = Field(default=None, min_length=1, max_length=500)

    valor: Optional[Decimal] = Field(default=None, gt=0)

    tipo: Optional[Literal["CREDITO", "DEBITO"]] = None

    documento: Optional[str] = None

    conciliado: Optional[bool] = None

    saldo: Optional[Decimal] = None

    @field_validator("tipo", mode="before")
    @classmethod
    def validar_tipo(cls, value):
        return _normalizar_tipo(_vazio_para_none(value))

    @field_validator("documento", "saldo", "data_transacao", "bank_account_id", mode="before")
    @classmethod
    def limpar_vazios(cls, value):
        return _vazio_para_none(value)

    @field_validator("valor", mode="before")
    @classmethod
    def valor_positivo(cls, value):
        value = _vazio_para_none(value)
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", ".") \
                if "," in value else value
        return abs(Decimal(str(value))) if value is not None else value

    @field_validator("descricao", mode="before")
    @classmethod
    def limpar_descricao(cls, value):
        return value.strip() if isinstance(value, str) else value


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
