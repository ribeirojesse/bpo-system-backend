"""Leitura da fatura de cartão de crédito SEM IA, tolerante a layouts.

A linha típica de fatura é previsível — data no começo, estabelecimento no
meio, valor no fim —, mas duas coisas estragam a leitura ingênua:

1. **Fatura em duas colunas** (Itaú, entre outros): o PDF tem os
   lançamentos nacionais à esquerda e internacionais/serviços à direita.
   Quem lê o texto corrido junta a descrição de uma coluna com o valor da
   outra. Por isso aqui as colunas são detectadas pela posição das datas
   na página e cada uma é lida separadamente.

2. **Seções que não são da fatura atual**: "compras parceladas — próximas
   faturas", simulações de parcelamento, limites e encargos futuros. São
   lançamentos de verdade, com data e valor, mas não entram nesta fatura.
   Cada coluna carrega o estado da seção em que está e ignora o que vem
   depois de um cabeçalho de seção futura/simulação.

Créditos (estorno, devolução, desconto, pagamento) viram item com valor
NEGATIVO — é o que faz a soma dos itens fechar com o total da fatura.

Funções puras sobre o que o pdfplumber extrai, reaproveitando os
utilitários do parser da folha. Sem banco, sem rede.
"""

import re

from decimal import Decimal

from app.services.payroll_pdf_parser import (
    extrair_paginas,
    sem_acento,
)


# ----------------------------------------------------------------------
# Padrões
# ----------------------------------------------------------------------

# "12/09", "12/09/2026", "12.09.26"
_RE_DATA = re.compile(
    r"^(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?$"
)

# Valor com centavos obrigatórios: 1.234,56 | 123,45 | -123,45 | 123,45-
_RE_MONEY = re.compile(
    r"^-?(?:R\$)?\s?-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}-?$"
)

# Valor em moeda estrangeira impresso junto da descrição.
_RE_MOEDA_ESTRANGEIRA = re.compile(
    r"\b(?:USD|EUR|US\$|U\$|GBP|ARS|CLP|BRL)\s*[\d.,]+",
    re.IGNORECASE
)

# Símbolo de moeda solto, sem número ("R$" separado do valor).
_RE_MOEDA_SOLTA = re.compile(
    r"(?<![A-Za-z])(?:R\$|RS|US\$|U\$|USD|EUR|BRL)(?![A-Za-z])",
    re.IGNORECASE
)

_RE_PARCELA = re.compile(
    r"(?:parc(?:ela)?\.?\s*)?(\d{1,2})\s*(?:/|de)\s*(\d{1,2})",
    re.IGNORECASE
)

# Seção por cartão/portador: "FINAL 1234", "(final 6170)", "CARTAO 1234".
_RE_FINAL_CARTAO = re.compile(
    r"(?:final|cart[aã]o|n[uú]mero)\s*(?:n[ou]\.?\s*)?[:\-]?\s*"
    r"[*•xX ]*(\d{4})",
    re.IGNORECASE
)

# Encargo que a fatura imprime sem data e que precisa entrar na soma.
# Deliberadamente estreito: "IOF R$ 44,48" solto aparece também nas
# simulações de parcelamento, que não são lançamento desta fatura.
_RE_ENCARGO_SEM_DATA = re.compile(
    r"^repasse de iof",
)


# ----------------------------------------------------------------------
# Seções
# ----------------------------------------------------------------------

# Cabeçalho que ABRE uma seção de lançamentos desta fatura.
_SECAO_ATUAL = (
    "lancamentos: compras e saques",
    "lancamentos internacionais",
    "lancamentos: produtos e servicos",
    "lancamentos nacionais",
    "lancamentos atuais",
    "lancamentos da fatura",
    "compras e saques",
    "transacoes",
    "demonstrativo",
    "despesas do periodo",
    "movimentacao",
)

# Cabeçalho que FECHA: o que vem depois não é desta fatura.
_SECAO_FUTURA = (
    "proximas faturas",
    "proxima fatura",
    "faturas futuras",
    "compras parceladas",
    "parcelas a vencer",
    "simulacao",
    "limites de credito",
    "encargos cobrados",
    "encargos do proximo",
    "demais taxas",
    "taxas de juros",
    "novo teto de juros",
    "credito rotativo",
    "opcoes de parcelamento",
    "parcelamento da fatura",
    "saque cash",
    # Saldo/pagamento da fatura passada: já foi cobrado antes.
    "fatura anterior",
    "resumo da fatura",
)

# Linha que nunca é lançamento (total, limite, aviso).
_PALAVRAS_IGNORAR = (
    "total",
    "subtotal",
    "limite",
    "pagamento minimo",
    "valor minimo",
    "saldo em aberto",
    "saldo financiado",
    "melhor dia",
    "fechamento",
    "central de atendimento",
    "ouvidoria",
    "cnpj",
    "pagina ",
    "www.",
    "dolar de conversao",
    "data estabelecimento",
    "data produtos",
)

# Rótulos do total da fatura, do mais específico pro mais genérico. O
# primeiro que casar ganha — "total da fatura anterior" e as simulações
# de parcelamento ficam de fora pelos termos proibidos abaixo.
_ROTULOS_TOTAL = (
    "total desta fatura",
    "total dos lancamentos atuais",
    "total da sua fatura",
    "total desta sua fatura",
    "total a pagar desta fatura",
    "valor total da fatura",
    "total da fatura",
    "total a pagar",
)

_TERMOS_PROIBIDOS_TOTAL = (
    "anterior",
    "financiado",
    "minimo",
    "proxima",
    "proximas",
    "demais",
    "futuras",
    "parcela",
    "simulacao",
    "saque",
)

_PALAVRAS_VENCIMENTO = (
    "vencimento",
    "pagar ate",
    "data de pagamento",
)

_BANCOS = (
    "nubank", "itau", "bradesco", "santander", "banco do brasil",
    "caixa", "inter", "c6 bank", "c6bank", "btg", "sicredi", "sicoob",
    "original", "safra", "pagbank", "pagseguro", "mercado pago",
    "will bank", "neon", "digio", "porto", "banrisul", "brb",
    "unicred", "ailos",
)

# Palavras que indicam crédito quando o valor vem sem sinal.
_PALAVRAS_CREDITO = (
    "estorno",
    "credito de",
    "devolucao",
    "pagamento efetuado",
    "pagamento recebido",
    "pagamento de fatura",
    "pagto fatura",
    "desconto",
    "cashback",
    "reembolso",
)


# ----------------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------------

def _parse_valor(texto):
    """"1.234,56" / "-123,45" / "123,45-" / "R$ 10,00" → Decimal.
    Devolve None quando não é valor monetário."""

    bruto = (texto or "").strip()

    if not _RE_MONEY.match(bruto):
        return None

    negativo = bruto.startswith("-") or bruto.endswith("-")

    limpo = (
        bruto.replace("R$", "")
        .replace("-", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )

    try:
        valor = Decimal(limpo).quantize(Decimal("0.01"))
    except Exception:
        return None

    return -valor if negativo else valor


def _parse_data(texto):
    """"12/09" ou "12/09/2026" → (dia, mes, ano|None)."""

    match = _RE_DATA.match((texto or "").strip())

    if not match:
        return None

    dia = int(match.group(1))

    mes = int(match.group(2))

    if not (1 <= dia <= 31 and 1 <= mes <= 12):
        return None

    ano = match.group(3)

    if ano:
        ano = int(ano)
        if ano < 100:
            ano += 2000
    else:
        ano = None

    return dia, mes, ano


def _tem(norm, palavras):

    return any(palavra in norm for palavra in palavras)


# ----------------------------------------------------------------------
# Colunas
# ----------------------------------------------------------------------

# Espaço em branco que separa uma coluna da anterior. Menos que isso é
# só o espaço entre duas palavras da mesma coluna.
_VAO_COLUNA = 20


def colunas_da_pagina(linhas, tolerancia=14):
    """Descobre as colunas de lançamentos pela posição horizontal das
    datas que ABREM bloco — primeira palavra da linha, ou depois de um
    vão largo. Sem esse cuidado, a marca de parcela dentro da descrição
    ("MP*MERCADOLIVRE 06/10") viraria uma coluna falsa.

    Devolve os limites [(x_inicio, x_fim), ...]; uma lista com um único
    intervalo aberto significa "página de uma coluna só"."""

    posicoes = []

    for linha in linhas:

        anterior = None

        for palavra in linha["palavras"]:

            abre_bloco = (
                anterior is None
                or palavra["x0"] - anterior["x1"] >= _VAO_COLUNA
            )

            if abre_bloco and _parse_data(palavra["text"]):
                posicoes.append(palavra["x0"])

            anterior = palavra

    posicoes.sort()

    grupos = []

    for x in posicoes:

        if grupos and x - grupos[-1][-1] <= tolerancia:
            grupos[-1].append(x)
        else:
            grupos.append([x])

    # Uma coluna de verdade tem várias linhas de lançamento.
    ancoras = sorted(
        min(grupo) for grupo in grupos if len(grupo) >= 3
    )

    if len(ancoras) < 2:
        return [(float("-inf"), float("inf"))]

    limites = []

    for posicao, ancora in enumerate(ancoras):

        # A coluna vai da sua âncora até a âncora da coluna seguinte: o
        # valor fica à direita da descrição, ainda dentro da coluna.
        fim = (
            ancoras[posicao + 1]
            if posicao + 1 < len(ancoras)
            else float("inf")
        )

        limites.append((ancora - 2, fim))

    # Tudo que estiver à esquerda da primeira âncora entra na primeira
    # coluna (recuo de cabeçalho, marcador de seção).
    limites[0] = (float("-inf"), limites[0][1])

    return limites


def _fatiar(linha, limite):
    """Devolve as palavras da linha dentro da coluna, em ordem."""

    inicio, fim = limite

    return [
        palavra
        for palavra in linha["palavras"]
        if inicio <= palavra["x0"] < fim
    ]


# ----------------------------------------------------------------------
# Leitura dos lançamentos
# ----------------------------------------------------------------------

def _item_da_linha(palavras, estado):
    """Transforma as palavras de uma linha de coluna em item, ou devolve
    None. O segundo valor diz se a linha tinha data e valor mas não deu
    pra aproveitar (pra contar como ignorada)."""

    textos = [palavra["text"] for palavra in palavras]

    if len(textos) < 2:
        return None, False

    data = _parse_data(textos[0])

    norm = sem_acento(" ".join(textos))

    # Encargo sem data que precisa entrar na soma (repasse de IOF).
    encargo = (
        data is None
        and bool(_RE_ENCARGO_SEM_DATA.match(norm))
    )

    if data is None and not encargo:
        return None, False

    indice_valor = None

    for posicao in range(len(textos) - 1, 0, -1):

        if _parse_valor(textos[posicao]) is not None:
            indice_valor = posicao
            break

    if indice_valor is None:
        return None, data is not None

    valor = _parse_valor(textos[indice_valor])

    if valor == 0:
        return None, False

    # Sinal impresso como token separado ("... DIF - 83,25").
    if textos[indice_valor - 1].strip() in {"-", "–", "—"}:
        valor = -abs(valor)

    inicio_descricao = 1 if data else 0

    descricao = " ".join(textos[inicio_descricao:indice_valor])

    descricao = _RE_MOEDA_ESTRANGEIRA.sub("", descricao)

    descricao = _RE_MOEDA_SOLTA.sub(" ", descricao)

    descricao = re.sub(
        r"\s+", " ", descricao
    ).strip(" -:;,.")

    if len(descricao) < 2 or not re.search(
        r"[A-Za-zÀ-ÿ]", descricao
    ):
        return None, data is not None

    if valor > 0 and _tem(
        sem_acento(descricao),
        _PALAVRAS_CREDITO
    ):
        valor = -valor

    parcela = None

    match_parcela = _RE_PARCELA.search(descricao)

    if match_parcela:

        atual = int(match_parcela.group(1))

        total = int(match_parcela.group(2))

        if 1 <= atual <= total <= 99:
            parcela = f"{atual:02d}/{total:02d}"

    return {
        "dia": data[0] if data else None,
        "mes": data[1] if data else None,
        "ano": data[2] if data else None,
        "descricao": descricao[:200],
        "valor": valor,
        "parcela": parcela,
        "cartao": estado.get("cartao"),
    }, False


def _itens_da_coluna(linhas, limite, estado):
    """Lê uma coluna da página inteira, respeitando as seções."""

    itens = []

    ignoradas = 0

    for linha in linhas:

        palavras = _fatiar(linha, limite)

        if not palavras:
            continue

        texto = " ".join(p["text"] for p in palavras)

        norm = sem_acento(texto)

        # Troca de seção. Só linha curta conta como cabeçalho: no meio
        # de um parágrafo ("...cobrado na próxima fatura com juros...")
        # as mesmas palavras não querem dizer troca de seção.
        if len(texto) <= 60:

            if _tem(norm, _SECAO_FUTURA):
                estado["atual"] = False
                continue

            if _tem(norm, _SECAO_ATUAL):
                estado["atual"] = True
                continue

        final = _RE_FINAL_CARTAO.search(texto)

        if final and not _parse_data(palavras[0]["text"]):
            estado["cartao"] = final.group(1)

        if not estado.get("atual", True):
            continue

        if _tem(norm, _PALAVRAS_IGNORAR):
            continue

        item, pulada = _item_da_linha(palavras, estado)

        if item:
            itens.append(item)

        elif pulada:
            ignoradas += 1

    return itens, ignoradas


# ----------------------------------------------------------------------
# Rótulos da fatura (total, vencimento, banco)
# ----------------------------------------------------------------------

def _total_declarado(paginas):

    candidatos = {}

    for pagina in paginas:

        for linha in pagina["linhas"]:

            norm = linha["norm"]

            if _tem(norm, _TERMOS_PROIBIDOS_TOTAL):
                continue

            for rotulo in _ROTULOS_TOTAL:

                if rotulo not in norm or rotulo in candidatos:
                    continue

                for palavra in reversed(linha["palavras"]):

                    valor = _parse_valor(palavra["text"])

                    if valor is not None and valor != 0:
                        candidatos[rotulo] = abs(valor)
                        break

    for rotulo in _ROTULOS_TOTAL:

        if rotulo in candidatos:
            return candidatos[rotulo]

    return None


def _vencimento_declarado(paginas):
    """Procura a data com ano na linha do rótulo "vencimento" e, quando
    o rótulo está sozinho num cabeçalho de colunas, na linha seguinte
    ("vencimento: / data de fechamento:" e depois "11/09/2026")."""

    for pagina in paginas:

        linhas = pagina["linhas"]

        for posicao, linha in enumerate(linhas):

            if not _tem(linha["norm"], _PALAVRAS_VENCIMENTO):
                continue

            candidatas = [linha]

            if posicao + 1 < len(linhas):
                candidatas.append(linhas[posicao + 1])

            for candidata in candidatas:

                for palavra in candidata["palavras"]:

                    data = _parse_data(palavra["text"])

                    if data and data[2]:
                        return data

    return None


def _banco_declarado(paginas):

    if not paginas:
        return None

    texto = sem_acento(paginas[0]["texto"])

    for banco in _BANCOS:

        if banco in texto:
            return banco.strip().upper()

    return None


# ----------------------------------------------------------------------
# Identificação do cartão/conta (conferência com a transação)
# ----------------------------------------------------------------------

# "final 1234", "(final 5874)", "FINAL: 0889"
_RE_FINAL_ROTULO = re.compile(
    r"(?:final|finais)\s*(?:n[ou]\.?\s*)?[:\-]?\s*[*•xX ]*(\d{4})\b",
    re.IGNORECASE
)

# Número mascarado: "4303.XXXX.XXXX.0889", "0004 XXXX XXXX 8475",
# "**** **** **** 1234"
_RE_NUMERO_MASCARADO = re.compile(
    r"(?:[\dxX*•]{4}[ .\-]){2,3}(\d{4})\b"
)


def finais_no_texto(texto):
    """Devolve os finais de cartão/conta citados no texto (4 dígitos).
    Usado pra conferir se a fatura é mesmo a do cartão da transação."""

    achados = set()

    for regex in (_RE_FINAL_ROTULO, _RE_NUMERO_MASCARADO):

        for match in regex.finditer(texto or ""):
            achados.add(match.group(1))

    return achados


def banco_no_texto(texto):
    """Nome do banco citado no texto, na grafia da lista interna."""

    norm = sem_acento(texto or "")

    for banco in _BANCOS:

        if banco in norm:
            return banco.strip().upper()

    return None


# ----------------------------------------------------------------------
# API do módulo
# ----------------------------------------------------------------------

def ler(conteudo: bytes):
    """Lê a fatura e devolve:
    {
      "itens": [{"dia","mes","ano","descricao","valor","parcela",
                 "cartao"}],
      "ignoradas": int,
      "total_documento": Decimal | None,
      "vencimento": (dia, mes, ano) | None,
      "banco": str | None,
      "tem_texto": bool,
      "colunas": int,
    }"""

    paginas = extrair_paginas(conteudo)

    finais = set()

    for pagina in paginas:
        finais |= finais_no_texto(pagina["texto"])

    itens = []

    ignoradas = 0

    colunas_vistas = 1

    # O final do cartão atravessa páginas; a seção recomeça em cada
    # página (o cabeçalho é repetido quando a seção continua).
    cartao_atual = {"cartao": None}

    for pagina in paginas:

        limites = colunas_da_pagina(pagina["linhas"])

        colunas_vistas = max(colunas_vistas, len(limites))

        for limite in limites:

            estado = {
                "cartao": cartao_atual["cartao"],
                "atual": True,
            }

            da_coluna, puladas = _itens_da_coluna(
                pagina["linhas"],
                limite,
                estado
            )

            cartao_atual["cartao"] = estado.get("cartao")

            itens.extend(da_coluna)

            ignoradas += puladas

    return {
        "itens": itens,
        "ignoradas": ignoradas,
        "total_documento": _total_declarado(paginas),
        "vencimento": _vencimento_declarado(paginas),
        "banco": _banco_declarado(paginas),
        "finais": sorted(finais),
        "tem_texto": any(
            p["texto"].strip() for p in paginas
        ),
        "colunas": colunas_vistas,
    }


__all__ = [
    "ler",
    "colunas_da_pagina",
    "finais_no_texto",
    "banco_no_texto",
]
