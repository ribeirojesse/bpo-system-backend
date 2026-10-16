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

    # Conta bancária em que o lançamento foi liquidado — vem da
    # conciliação com o extrato ou do lote de folha/fatura de cartão
    # (ver DreService._mapa_banco_por_lancamento). Nulo em lançamento
    # ainda não conciliado.
    conta_nome: Optional[str] = None


class PortalBreakdownItemSchema(BaseModel):

    # Uma linha de quebra por categoria/subcategoria/fornecedor. "outros"
    # marca o agregado do que passou do teto de séries coloridas do
    # gráfico (ver dataviz skill) — nunca uma categoria de verdade.
    id: str

    nome: str

    valor: Decimal

    outros: bool = False


class PortalEvolucaoMensalSchema(BaseModel):

    mes: str

    pago: Decimal

    recebido: Decimal

    # Recebido − pago no mês. Antes era calculado no navegador; vem
    # pronto pra tela e o gráfico não precisar recalcular.
    resultado: Decimal = Decimal("0")


class PortalResumoMesSchema(BaseModel):
    """Fechamento de um mês: o que entrou, o que saiu e a diferença."""

    label: str

    recebido: Decimal

    pago: Decimal

    resultado: Decimal


class PortalEmAbertoSchema(BaseModel):
    """O que ainda não foi liquidado (status PENDENTE)."""

    a_pagar: Decimal

    a_receber: Decimal

    a_pagar_vencido: Decimal

    a_receber_vencido: Decimal


class PortalVencimentoSchema(BaseModel):

    id: uuid.UUID

    tipo: str

    descricao: str

    valor: Decimal

    vencimento: date

    # Negativo = já venceu.
    dias: int

    contato_nome: Optional[str] = None


class PortalDashboardSchema(BaseModel):

    # Sem saldo em conta aqui de propósito — o cliente não monitora saldo
    # bancário nesse sistema, "saldo_inicial" é só um valor de cadastro,
    # não um saldo mantido/atualizado.
    total_pago: Decimal

    total_recebido: Decimal

    saldo_periodo: Decimal

    contas_bancarias: list[PortalContaBancariaSchema] = []

    despesas_por_categoria: list[PortalBreakdownItemSchema] = []

    despesas_por_subcategoria: list[PortalBreakdownItemSchema] = []

    receitas_por_categoria: list[PortalBreakdownItemSchema] = []

    receitas_por_subcategoria: list[PortalBreakdownItemSchema] = []

    maiores_fornecedores: list[PortalBreakdownItemSchema] = []

    evolucao_mensal: list[PortalEvolucaoMensalSchema] = []

    # Recortes novos do dashboard: fechamento do mês corrente, do mês
    # anterior (pra comparação), o que está em aberto e os próximos
    # vencimentos.
    mes_atual: Optional[PortalResumoMesSchema] = None

    mes_anterior: Optional[PortalResumoMesSchema] = None

    em_aberto: Optional[PortalEmAbertoSchema] = None

    proximos_vencimentos: list[PortalVencimentoSchema] = []
