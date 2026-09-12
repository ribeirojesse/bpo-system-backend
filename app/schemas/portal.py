import uuid

from datetime import date

from decimal import Decimal

from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict
)


# Schemas do portal do CLIENTE — sempre só-leitura (o cliente não cria,
# edita nem exclui nada por aqui, ver app/api/endpoints/portal.py).


class PortalContaBancariaSchema(BaseModel):

    id: uuid.UUID

    banco: str

    agencia: Optional[str] = None

    conta: str

    tipo_conta: Optional[str] = None

    saldo_inicial: Decimal

    ativo: bool

    model_config = ConfigDict(
        from_attributes=True
    )


class PortalFornecedorSchema(BaseModel):

    id: uuid.UUID

    nome: str

    documento: Optional[str] = None

    email: Optional[str] = None

    telefone: Optional[str] = None

    tipo: str

    ativo: bool

    model_config = ConfigDict(
        from_attributes=True
    )


class PortalSubcategoriaSchema(BaseModel):

    id: uuid.UUID

    nome: str

    ativo: bool

    model_config = ConfigDict(
        from_attributes=True
    )


class PortalCategoriaSchema(BaseModel):

    id: uuid.UUID

    nome: str

    ativo: bool

    subcategorias: list[PortalSubcategoriaSchema] = []

    model_config = ConfigDict(
        from_attributes=True
    )


class PortalLancamentoSchema(BaseModel):

    id: uuid.UUID

    # "PAGAR" ou "RECEBER" — indica se veio de accounts_payable ou de
    # accounts_receivable, já que o portal mostra os dois juntos numa
    # única lista de lançamentos.
    tipo: str

    descricao: str

    valor: Decimal

    vencimento: date

    data_liquidacao: Optional[date] = None

    competencia: Optional[str] = None

    status: str

    fornecedor_nome: Optional[str] = None

    categoria_nome: Optional[str] = None


class PortalDashboardSchema(BaseModel):

    saldo_contas: Decimal

    total_pago: Decimal

    total_recebido: Decimal

    total_a_pagar: Decimal

    total_a_receber: Decimal

    contas_bancarias: list[PortalContaBancariaSchema] = []
