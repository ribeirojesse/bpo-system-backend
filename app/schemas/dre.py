import uuid

from typing import Optional, Literal

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


ModoDre = Literal["CATEGORIA", "BANCO", "BANCO_CATEGORIA"]

TipoBloco = Literal["RECEITA", "DESPESA"]


class DreBlocoConfigSchema(BaseModel):
    """Um bloco/linha do relatório: um nome de exibição agrupando uma ou
    mais categorias (ex.: "Custos com Pessoal" = Folha + Encargos +
    Benefícios). Só é aplicado no modo CATEGORIA."""

    nome: str

    tipo: TipoBloco

    category_ids: list[uuid.UUID] = []

    ordem: int = 0


class DreTemplateCreateSchema(BaseModel):

    # Nulo = modelo "padrão da carteira" (só ADMIN pode criar assim; o
    # portal do CLIENTE sempre grava com o próprio client_id, ver
    # DreService.create_template).
    client_id: Optional[uuid.UUID] = None

    nome: str

    modo: ModoDre = "CATEGORIA"

    cor_destaque: Optional[str] = None

    blocos: list[DreBlocoConfigSchema] = []


class DreTemplateUpdateSchema(BaseModel):

    nome: Optional[str] = None

    modo: Optional[ModoDre] = None

    cor_destaque: Optional[str] = None

    blocos: Optional[list[DreBlocoConfigSchema]] = None

    ativo: Optional[bool] = None


class DreTemplateResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: Optional[uuid.UUID] = None

    nome: str

    modo: ModoDre

    cor_destaque: Optional[str] = None

    blocos: list[DreBlocoConfigSchema] = []

    ativo: bool

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, template):
        """O model SQLAlchemy guarda os blocos dentro de `config`
        (JSONB) — extraídos aqui porque o schema de resposta expõe
        `blocos` direto, mais conveniente pro frontend."""

        return cls(
            id=template.id,
            client_id=template.client_id,
            nome=template.nome,
            modo=template.modo,
            cor_destaque=template.cor_destaque,
            blocos=(template.config or {}).get("blocos", []),
            ativo=template.ativo,
        )


class DreGerarRequestSchema(BaseModel):

    # Ignorado pro CLIENTE (o backend sempre usa o client_id do próprio
    # login) — obrigatório pro ADMIN, que pode gerar pra qualquer
    # cliente da carteira (ver DreService._resolve_client_id).
    client_id: Optional[uuid.UUID] = None

    ano: int

    modo: ModoDre = "CATEGORIA"

    template_id: Optional[uuid.UUID] = None

    # Filtra o relatório a uma única conta bancária — funciona tanto
    # como recorte dentro do modo CATEGORIA quanto como parte do
    # agrupamento nos modos BANCO/BANCO_CATEGORIA.
    bank_account_id: Optional[uuid.UUID] = None

    incluir_saldo_contas: bool = True


class DreLinhaSchema(BaseModel):

    nome: str

    tipo: TipoBloco

    valores_mensais: list[Decimal]

    total: Decimal

    # Detalhamento opcional por subcategoria, só populado no modo
    # CATEGORIA e só quando a categoria/bloco tem lançamentos com
    # subcategoria definida — o frontend decide se exibe ou não (ver
    # DreTemplateEditorModal/ReportsPage, toggle "Mostrar subcategorias").
    subcategorias: list["DreLinhaSchema"] = []


class DreSaldoContaSchema(BaseModel):

    banco: str

    conta: str

    saldo: Decimal


class DreResultadoSchema(BaseModel):

    cliente_nome: str

    ano: int

    modo: ModoDre

    meses: list[str]

    linhas_receita: list[DreLinhaSchema]

    linhas_despesa: list[DreLinhaSchema]

    totais_receita: list[Decimal]

    totais_despesa: list[Decimal]

    totais_resultado: list[Decimal]

    receita_anual: Decimal

    despesa_anual: Decimal

    resultado_anual: Decimal

    saldos_contas: list[DreSaldoContaSchema] = []

    cor_destaque: Optional[str] = None
