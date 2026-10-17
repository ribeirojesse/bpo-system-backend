import uuid

from typing import Optional, Literal

from datetime import date

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


ModoDre = Literal["CATEGORIA", "BANCO", "BANCO_CATEGORIA"]

TipoBloco = Literal["RECEITA", "DESPESA"]

# Como a linha entra no relatório:
#   NORMAL       aparece e soma no resultado;
#   INFORMATIVO  aparece num quadro à parte, FORA das somas (ex.:
#                transferência entre contas, aplicação/resgate);
#   OCULTO       não aparece e não soma.
ModoLinha = Literal["NORMAL", "INFORMATIVO", "OCULTO"]


class DreBlocoConfigSchema(BaseModel):
    """Um bloco/linha do relatório: um nome de exibição agrupando uma ou
    mais categorias (ex.: "Custos com Pessoal" = Folha + Encargos +
    Benefícios). Só é aplicado no modo CATEGORIA."""

    nome: str

    tipo: TipoBloco

    category_ids: list[uuid.UUID] = []

    ordem: int = 0

    modo: ModoLinha = "NORMAL"


class DreCategoriaConfigSchema(BaseModel):
    """Ajuste de uma categoria que não está em nenhum bloco: serve pra
    tirar do relatório ou jogar no quadro de só-visualização sem
    precisar criar um bloco só pra ela."""

    category_id: uuid.UUID

    modo: ModoLinha = "NORMAL"

    # Renomeia a categoria só na exibição do relatório.
    nome_exibicao: Optional[str] = None


class DreLinhaManualSchema(BaseModel):
    """Valor digitado à mão, que não vem de lançamento nenhum: provisão,
    rateio de outra empresa, estimativa. Fica salvo no modelo, então
    vale toda vez que o relatório é gerado com ele."""

    nome: str

    tipo: TipoBloco

    valor: Decimal

    # "MM/AAAA" = entra só nesse mês; nulo = repete o valor em todos os
    # meses do exercício.
    competencia: Optional[str] = None

    modo: ModoLinha = "NORMAL"

    observacao: Optional[str] = None


class DreQuadroLinhaSchema(BaseModel):
    """Uma linha de quadro digitada à mão (ex.: "Sicredi" /
    203.105,60)."""

    nome: str

    valor: Decimal


class DreQuadroSchema(BaseModel):
    """Quadro de valores digitados, fora da grade mensal — nasceu do
    "Valores em Aplicação" que o usuário montava à mão no script antigo
    (saldo de cada aplicação na data do fechamento). Só sai no PDF, e
    nunca entra em receita, despesa ou resultado."""

    titulo: str = "Valores em Aplicação"

    # Texto livre no subtítulo do quadro (ex.: "Posição em
    # 21/09/2026").
    referencia: Optional[str] = None

    linhas: list[DreQuadroLinhaSchema] = []

    # false = esconde a linha de TOTAL (quadro de um item só, por ex.).
    mostrar_total: bool = True


class DreAjusteSchema(BaseModel):
    """Ajuste do resultado: pega os lançamentos de certas categorias,
    faz entradas − saídas mês a mês e abate (ou soma) esse saldo do
    resultado, gerando a linha "Resultado Final" no resumo.

    É o caso do "Fundo Não Utilizável" da APAE: dinheiro que entrou mas
    não pode ser usado, então não deveria contar como resultado do mês.

    O saldo é calculado sobre os lançamentos das categorias marcadas
    INDEPENDENTEMENTE de elas aparecerem nas tabelas — quem decide isso
    é o modo da categoria (NORMAL / INFORMATIVO / OCULTO). Marcar a
    categoria como "Só visualização" e usá-la num ajuste é a combinação
    que tira o valor do resultado e ainda mostra quanto foi."""

    nome: str

    category_ids: list[uuid.UUID] = []

    # SUBTRAIR: Resultado Final = Resultado − saldo do ajuste.
    # SOMAR:    Resultado Final = Resultado + saldo do ajuste.
    operacao: Literal["SUBTRAIR", "SOMAR"] = "SUBTRAIR"


class DreTemplateCreateSchema(BaseModel):

    # Nulo = modelo "padrão da carteira" (só ADMIN pode criar assim; o
    # portal do CLIENTE sempre grava com o próprio client_id, ver
    # DreService.create_template).
    client_id: Optional[uuid.UUID] = None

    nome: str

    modo: ModoDre = "CATEGORIA"

    cor_destaque: Optional[str] = None

    blocos: list[DreBlocoConfigSchema] = []

    categorias: list[DreCategoriaConfigSchema] = []

    linhas_manuais: list[DreLinhaManualSchema] = []

    quadros: list[DreQuadroSchema] = []

    ajustes: list[DreAjusteSchema] = []


class DreTemplateUpdateSchema(BaseModel):

    nome: Optional[str] = None

    modo: Optional[ModoDre] = None

    cor_destaque: Optional[str] = None

    blocos: Optional[list[DreBlocoConfigSchema]] = None

    categorias: Optional[list[DreCategoriaConfigSchema]] = None

    linhas_manuais: Optional[list[DreLinhaManualSchema]] = None

    quadros: Optional[list[DreQuadroSchema]] = None

    ajustes: Optional[list[DreAjusteSchema]] = None

    ativo: Optional[bool] = None


class DreTemplateResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: Optional[uuid.UUID] = None

    nome: str

    modo: ModoDre

    cor_destaque: Optional[str] = None

    blocos: list[DreBlocoConfigSchema] = []

    categorias: list[DreCategoriaConfigSchema] = []

    linhas_manuais: list[DreLinhaManualSchema] = []

    quadros: list[DreQuadroSchema] = []

    ajustes: list[DreAjusteSchema] = []

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
            categorias=(template.config or {}).get("categorias", []),
            linhas_manuais=(
                (template.config or {}).get("linhas_manuais", [])
            ),
            quadros=(template.config or {}).get("quadros", []),
            ajustes=(template.config or {}).get("ajustes", []),
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

    # Meses a incluir (1 = janeiro ... 12 = dezembro). Nulo ou os 12
    # meses = exercício inteiro. Usado pela exportação em PDF, que
    # precisa sair com os mesmos meses marcados na tela; os totais são
    # recalculados só com os meses escolhidos.
    meses: Optional[list[int]] = Field(
        default=None,
        min_length=1,
        max_length=12
    )

    # true = o PDF sai com as subcategorias detalhadas embaixo de cada
    # categoria, como o toggle "Mostrar subcategorias" da tela.
    subcategorias: bool = False


class LancamentosExcelRequestSchema(BaseModel):
    """Exportação dos lançamentos em Excel: o único filtro é o período
    personalizado (data inicial e final, inclusive). client_id segue a
    mesma regra do DRE — ignorado pro CLIENTE, obrigatório pro ADMIN."""

    client_id: Optional[uuid.UUID] = None

    data_inicio: date

    data_fim: date

    # Opcional: limita a planilha aos lançamentos conciliados com essa
    # conta bancária (o banco de um lançamento vem do vínculo de
    # conciliação com a transação do extrato).
    bank_account_id: Optional[uuid.UUID] = None


class DreLinhaSchema(BaseModel):

    nome: str

    tipo: TipoBloco

    valores_mensais: list[Decimal]

    total: Decimal

    # true = valor digitado no modelo, não veio de lançamento.
    manual: bool = False

    # Fora das somas (quadro de só-visualização).
    informativo: bool = False

    # Detalhamento opcional por subcategoria, só populado no modo
    # CATEGORIA e só quando a categoria/bloco tem lançamentos com
    # subcategoria definida — o frontend decide se exibe ou não (ver
    # DreTemplateEditorModal/ReportsPage, toggle "Mostrar subcategorias").
    subcategorias: list["DreLinhaSchema"] = []


class DreQuadroResultadoSchema(BaseModel):
    """Quadro digitado, já com o total somado pelo backend."""

    titulo: str

    referencia: Optional[str] = None

    linhas: list[DreQuadroLinhaSchema] = []

    total: Decimal

    mostrar_total: bool = True


class DreAjusteResultadoSchema(BaseModel):
    """Saldo mensal de um ajuste (entradas − saídas das categorias
    marcadas) e como ele entra no Resultado Final."""

    nome: str

    valores_mensais: list[Decimal]

    total: Decimal

    operacao: Literal["SUBTRAIR", "SOMAR"] = "SUBTRAIR"


class DreResultadoSchema(BaseModel):

    cliente_nome: str

    ano: int

    modo: ModoDre

    meses: list[str]

    # Texto dos meses quando o relatório foi recortado ("jan, fev") —
    # nulo no exercício inteiro. O PDF usa no subtítulo.
    meses_filtro: Optional[str] = None

    # Ecoa o pedido de detalhar subcategorias (o PDF usa; a tela tem o
    # próprio toggle).
    mostrar_subcategorias: bool = False

    linhas_receita: list[DreLinhaSchema]

    linhas_despesa: list[DreLinhaSchema]

    # Linhas marcadas como "só visualização" no modelo: aparecem num
    # quadro à parte e NÃO entram em receita, despesa nem resultado.
    linhas_informativas: list[DreLinhaSchema] = []

    totais_receita: list[Decimal]

    totais_despesa: list[Decimal]

    totais_resultado: list[Decimal]

    # Quadros digitados no modelo (hoje só renderizados no PDF).
    quadros: list[DreQuadroResultadoSchema] = []

    # Ajustes do modelo e o resultado depois deles. Quando não há
    # ajuste nenhum, `linhas_ajuste` vem vazia e
    # `totais_resultado_final` repete `totais_resultado`.
    linhas_ajuste: list[DreAjusteResultadoSchema] = []

    totais_resultado_final: list[Decimal] = []

    receita_anual: Decimal

    despesa_anual: Decimal

    resultado_anual: Decimal

    resultado_final_anual: Decimal = Decimal("0")

    cor_destaque: Optional[str] = None

    # Nome da conta bancária quando o relatório foi filtrado por uma.
    conta_filtro: Optional[str] = None
