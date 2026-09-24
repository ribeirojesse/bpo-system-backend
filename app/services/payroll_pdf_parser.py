"""Leitura de comprovante de folha SEM IA, tolerante a layouts diferentes.

Em vez de supor um formato fixo de linha ("nome CPF valor"), roda várias
estratégias e fica com a leitura mais coerente:

1. **Âncora no CPF (por posição na página)** — cada pagamento de folha
   quase sempre tem o CPF do favorecido. Cada linha visual com um CPF e
   um valor monetário vira um registro; o nome é o texto da coluna de
   nome (à esquerda do CPF), incluindo pedaços de nome quebrados em
   linhas acima/abaixo (célula com quebra de linha, comum no Itaú). O
   cabeçalho da tabela ("Nome/Funcionário/Favorecido", "CPF", "Valor/
   Líquido"), quando existe, delimita as colunas — assim o número de
   ordem da linha (BB) e colunas como agência/conta/situação não entram
   no nome, e o valor certo é escolhido quando há mais de um na linha.
2. **Rótulo: valor** — layouts em bloco ("Favorecido: X", "CPF: Y",
   "Valor: Z"), um funcionário por bloco.
3. **Linha simples** — o parser antigo (nome ... valor), melhorado, pra
   documentos sem CPF.

A escolha usa o que o sistema já sabe: a leitura cuja soma bate com o
valor da transação do extrato ganha; depois, a que bate com o total
declarado no próprio documento; depois, a que bate com a quantidade de
pagamentos declarada.

Funções puras sobre as palavras/linhas extraídas pelo pdfplumber — sem
banco, sem rede.
"""

import io
import re
import unicodedata

from decimal import Decimal, InvalidOperation

import pdfplumber


# ----------------------------------------------------------------------
# Padrões
# ----------------------------------------------------------------------

_RE_MONEY = re.compile(
    r"^(?:R\$)?-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}-?$"
)

_RE_CPF = re.compile(
    r"^[\d*Xx]{3}\.[\d*Xx]{3}\.[\d*Xx]{3}-[\d*Xx]{2}$"
)

_RE_CNPJ = re.compile(
    r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$"
)

_RE_CPF_TEXTO = re.compile(
    r"[\d*]{3}\.?[\d*]{3}\.?[\d*]{3}-?[\d*]{2}"
)

_RE_MONEY_TEXTO = re.compile(
    r"(?:R\$\s*)?((?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})"
)

# Situação da linha que indica que o dinheiro NÃO saiu (não entra na
# folha). Comparado sem acento e em minúsculas.
_RE_STATUS_FALHA = re.compile(
    r"rejeitad|devolvid|cancelad|estornad|recusad|"
    r"nao efetuad|nao pago|nao realizad|com erro|inconsisten"
)

_PALAVRAS_NOME = (
    "nome", "funcionario", "favorecido", "beneficiario",
    "colaborador", "empregado", "servidor", "destinatario",
)

_PALAVRAS_CPF = ("cpf", "cpf/cnpj", "documento", "cpf/cnpj:")

_PALAVRAS_VALOR = (
    "valor", "liquido", "valor(r$)", "vl.", "vlr", "vlr.", "creditado",
)

_PALAVRAS_TOTAL = ("total", "subtotal", "totais", "soma")

_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Linhas com a mesma altura (top) até essa distância são a mesma linha.
_TOLERANCIA_LINHA = 2.5

# Pedaço de nome quebrado: até essa distância vertical da linha do CPF.
_DISTANCIA_CONTINUACAO = 12.0

# Distância horizontal entre palavras que indica mudança de coluna.
_ESPACO_COLUNA = 15.0

TOLERANCIA_SOMA = Decimal("1.00")


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------

def sem_acento(texto):

    texto = unicodedata.normalize("NFKD", texto or "")

    return "".join(
        c for c in texto if not unicodedata.combining(c)
    ).lower()


def parse_money(texto):

    texto = (texto or "").replace("R$", "").strip().strip("-")

    try:
        return Decimal(
            texto.replace(".", "").replace(",", ".")
        ).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _is_money(texto):

    return bool(_RE_MONEY.match(texto or ""))


def _is_doc(texto):

    return bool(
        _RE_CPF.match(texto or "")
        or _RE_CNPJ.match(texto or "")
    )


def _tem_letras(texto):

    return bool(re.search(r"[A-Za-zÀ-ÿ]", texto or ""))


def _limpar_nome(partes):

    nome = " ".join(p for p in partes if p)

    nome = nome.replace("R$", " ")

    # Número de ordem no começo ("1 Fulano", "01 - Fulano").
    nome = re.sub(r"^\s*\d{1,4}\s*[-.)]?\s+", "", nome)

    nome = re.sub(r"\s+", " ", nome).strip(" -:;,.")

    return nome


# ----------------------------------------------------------------------
# Extração de palavras/linhas
# ----------------------------------------------------------------------

def extrair_paginas(conteudo: bytes):
    """Devolve [{"linhas": [[palavra,...],...], "texto": str}] por página.
    Cada palavra: dict com text, x0, x1, top, bottom."""

    paginas = []

    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:

        for page in pdf.pages:

            palavras = page.extract_words(
                keep_blank_chars=False,
                use_text_flow=False,
            )

            paginas.append({
                "linhas": agrupar_linhas(palavras),
                "texto": page.extract_text() or "",
            })

    return paginas


def agrupar_linhas(palavras):

    linhas = []

    for palavra in sorted(
        palavras,
        key=lambda w: (w["top"], w["x0"])
    ):
        if (
            linhas
            and abs(palavra["top"] - linhas[-1]["top"])
            <= _TOLERANCIA_LINHA
        ):
            linhas[-1]["palavras"].append(palavra)
        else:
            linhas.append({
                "top": palavra["top"],
                "palavras": [palavra],
            })

    for linha in linhas:
        linha["palavras"].sort(key=lambda w: w["x0"])
        linha["texto"] = " ".join(
            w["text"] for w in linha["palavras"]
        )
        linha["norm"] = sem_acento(linha["texto"])

    return linhas


# ----------------------------------------------------------------------
# Estratégia 1 — âncora no CPF, por posição
# ----------------------------------------------------------------------

def _detectar_cabecalho(linha):
    """Se a linha parece o cabeçalho da tabela, devolve as posições das
    colunas: {"nome_x0", "cpf_x0", "valor_xc"} (qualquer um pode faltar)."""

    tem_nome = tem_cpf = tem_valor = False
    colunas = {}

    for palavra in linha["palavras"]:

        t = sem_acento(palavra["text"]).strip(":")

        if any(t.startswith(p) for p in _PALAVRAS_NOME):
            tem_nome = True
            colunas.setdefault("nome_x0", palavra["x0"])

        elif t in _PALAVRAS_CPF or t.startswith("cpf"):
            tem_cpf = True
            colunas.setdefault("cpf_x0", palavra["x0"])

        elif any(t.startswith(p) for p in _PALAVRAS_VALOR):
            tem_valor = True
            # A coluna de valor "de verdade" costuma ser a última com
            # esse nome (ex.: "Valor bruto ... Valor líquido").
            colunas["valor_xc"] = (palavra["x0"] + palavra["x1"]) / 2

    if tem_nome and (tem_cpf or tem_valor) and not _is_linha_total(linha):
        return colunas

    return None


def _is_linha_total(linha):

    return any(
        re.search(rf"\b{p}\b", linha["norm"])
        for p in _PALAVRAS_TOTAL
    )


def estrategia_ancora_cpf(paginas):

    registros = []
    rejeitados = []

    cabecalho = None

    for pagina in paginas:

        linhas = pagina["linhas"]

        # Cabeçalho da página (se repetir em cada página, atualiza).
        for linha in linhas:
            detectado = _detectar_cabecalho(linha)
            if detectado:
                cabecalho = detectado
                break

        ancoras = []

        for idx, linha in enumerate(linhas):

            if _is_linha_total(linha):
                continue

            docs = [
                w for w in linha["palavras"]
                if _is_doc(w["text"])
            ]

            moneys = [
                w for w in linha["palavras"]
                if _is_money(w["text"])
                and (not docs or w["x0"] > docs[0]["x1"])
            ]

            if not docs or not moneys:
                continue

            doc = docs[0]

            # Valor: o mais perto da coluna "Valor" do cabeçalho; sem
            # cabeçalho, o último da linha.
            if cabecalho and "valor_xc" in cabecalho:
                valor_w = min(
                    moneys,
                    key=lambda w: abs(
                        (w["x0"] + w["x1"]) / 2
                        - cabecalho["valor_xc"]
                    )
                )
            else:
                valor_w = moneys[-1]

            ancoras.append({
                "idx": idx,
                "top": linha["top"],
                "doc": doc,
                "valor_w": valor_w,
                "linha": linha,
            })

        if not ancoras:
            continue

        # Limites da coluna de nome nesta página.
        limite_direito = min(a["doc"]["x0"] for a in ancoras)

        if cabecalho and "cpf_x0" in cabecalho:
            limite_direito = min(limite_direito, cabecalho["cpf_x0"])

        limite_esquerdo = (
            cabecalho["nome_x0"] - 4
            if cabecalho and "nome_x0" in cabecalho
            else None
        )

        def palavras_de_nome(linha):
            return [
                w for w in linha["palavras"]
                if w["x1"] <= limite_direito + 1
                and (
                    limite_esquerdo is None
                    or w["x0"] >= limite_esquerdo
                )
            ]

        indices_ancora = {a["idx"] for a in ancoras}

        # Linhas "só de nome" (continuação de nome quebrado): todas as
        # palavras dentro da coluna de nome, com letras, e fora de
        # cabeçalho/total. Cada uma vai pra âncora mais próxima.
        continuacoes = {a["idx"]: {"acima": [], "abaixo": []} for a in ancoras}

        for idx, linha in enumerate(linhas):

            if idx in indices_ancora:
                continue

            if (
                _is_linha_total(linha)
                or _detectar_cabecalho(linha)
                or not _tem_letras(linha["texto"])
            ):
                continue

            if any(
                w["x1"] > limite_direito + 1
                or (
                    limite_esquerdo is not None
                    and w["x0"] < limite_esquerdo
                )
                for w in linha["palavras"]
            ):
                continue

            mais_proxima = min(
                ancoras,
                key=lambda a: abs(a["top"] - linha["top"])
            )

            distancia = abs(mais_proxima["top"] - linha["top"])

            if distancia > _DISTANCIA_CONTINUACAO:
                continue

            lado = (
                "acima"
                if linha["top"] < mais_proxima["top"]
                else "abaixo"
            )

            continuacoes[mais_proxima["idx"]][lado].append(linha)

        for ancora in ancoras:

            partes = []

            for linha in continuacoes[ancora["idx"]]["acima"]:
                partes += [w["text"] for w in linha["palavras"]]

            partes += [
                w["text"] for w in palavras_de_nome(ancora["linha"])
            ]

            for linha in continuacoes[ancora["idx"]]["abaixo"]:
                partes += [w["text"] for w in linha["palavras"]]

            nome = _limpar_nome(partes)

            valor = parse_money(ancora["valor_w"]["text"])

            registro = {
                "funcionario": nome,
                "cpf": ancora["doc"]["text"],
                "valor": valor,
            }

            if _RE_STATUS_FALHA.search(ancora["linha"]["norm"]):
                rejeitados.append(registro)
                continue

            if nome and valor is not None and valor > 0:
                registros.append(registro)

    return registros, rejeitados


# ----------------------------------------------------------------------
# Estratégia 2 — blocos "Rótulo: valor"
# ----------------------------------------------------------------------

_RE_ROTULO_NOME = re.compile(
    r"\b(?:nome(?: do)?(?: favorecido| funcionario| beneficiario)?|"
    r"favorecido|beneficiario|funcionario|colaborador)\s*:\s*(.+)",
)

_RE_ROTULO_CPF = re.compile(
    r"\bcpf(?:/cnpj)?\s*(?:do favorecido)?\s*:\s*([\d*.\-/xX]{11,18})"
)

_RE_ROTULO_VALOR = re.compile(
    r"\b(?:valor(?: liquido| pago| creditado| do pagamento| do credito)?|"
    r"liquido)\s*(?:\(r\$\))?\s*:\s*(?:r\$\s*)?"
    r"((?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})"
)


def estrategia_rotulos(paginas):

    registros = []
    rejeitados = []

    atual = None

    def fechar():
        if atual and atual.get("funcionario") and atual.get("valor"):
            if atual.pop("_falha", False):
                rejeitados.append(atual)
            else:
                registros.append(atual)

    for pagina in paginas:

        for linha in pagina["linhas"]:

            norm = linha["norm"]
            original = linha["texto"]

            if _is_linha_total(linha):
                continue

            # Dados da empresa pagadora não são funcionário.
            if re.search(r"\b(empresa|pagador|remetente|debitad)", norm):
                continue

            m_nome = _RE_ROTULO_NOME.search(norm)

            if m_nome:
                fechar()
                inicio = m_nome.start(1)
                trecho = original[inicio:]
                # Corta o nome antes de outro rótulo na mesma linha.
                trecho = re.split(
                    r"\s+(?:CPF|Cpf|cpf|Valor|VALOR|Ag[eê]ncia|AG[EÊ]NCIA|Conta|CONTA)\b",
                    trecho
                )[0]
                atual = {
                    "funcionario": _limpar_nome([trecho]),
                    "cpf": None,
                    "valor": None,
                }

            if atual is None:
                continue

            m_cpf = _RE_ROTULO_CPF.search(norm)

            if m_cpf and not atual["cpf"]:
                atual["cpf"] = m_cpf.group(1)

            m_valor = _RE_ROTULO_VALOR.search(norm)

            if m_valor and not atual["valor"]:
                atual["valor"] = parse_money(m_valor.group(1))

            if _RE_STATUS_FALHA.search(norm):
                atual["_falha"] = True

    fechar()

    return registros, rejeitados


# ----------------------------------------------------------------------
# Estratégia 3 — linha simples (sem CPF)
# ----------------------------------------------------------------------

def estrategia_linhas(paginas):

    registros = []
    rejeitados = []

    for pagina in paginas:

        for linha in pagina["linhas"]:

            if _is_linha_total(linha) or _detectar_cabecalho(linha):
                continue

            moneys = [
                w for w in linha["palavras"]
                if _is_money(w["text"])
            ]

            if not moneys:
                continue

            # Nome: palavras antes do primeiro token com dígito (CPF,
            # conta, data, valor...).
            partes = []

            anterior = None

            for w in linha["palavras"]:
                if re.search(r"\d", w["text"]):
                    if partes:
                        break
                    continue
                # Espaço grande entre palavras = outra coluna.
                if (
                    partes
                    and anterior is not None
                    and w["x0"] - anterior["x1"] > _ESPACO_COLUNA
                ):
                    break
                partes.append(w["text"])
                anterior = w

            nome = _limpar_nome(partes)

            if (
                len(nome) < 3
                or len(re.findall(r"[A-Za-zÀ-ÿ]", nome)) < 3
                or ":" in nome
            ):
                continue

            m_cpf = _RE_CPF_TEXTO.search(linha["texto"])

            registro = {
                "funcionario": nome,
                "cpf": m_cpf.group(0) if m_cpf else None,
                "valor": parse_money(moneys[-1]["text"]),
            }

            if _RE_STATUS_FALHA.search(linha["norm"]):
                rejeitados.append(registro)
                continue

            if registro["valor"] and registro["valor"] > 0:
                registros.append(registro)

    return registros, rejeitados


# ----------------------------------------------------------------------
# Metadados do documento
# ----------------------------------------------------------------------

def total_declarado(paginas):

    for pagina in paginas:

        for linha in pagina["linhas"]:

            if not re.search(r"\btotal\b", linha["norm"]):
                continue

            for w in linha["palavras"]:
                if _is_money(w["text"]):
                    return parse_money(w["text"])

    return None


def quantidade_declarada(paginas):

    for pagina in paginas:

        texto = sem_acento(pagina["texto"])

        m = re.search(
            r"quantidade de (?:pagamentos|registros|creditos|"
            r"funcionarios|favorecidos)\s*:?\s*(\d{1,5})",
            texto
        ) or re.search(
            r"(?:total|totais)[^\n]*?\b(\d{1,5})\s+"
            r"(?:pagamentos|funcionarios|favorecidos|creditos|registros)",
            texto
        ) or re.search(
            r"\b(\d{1,5})\s+(?:pagamentos|funcionarios|favorecidos|"
            r"creditos)\b",
            texto
        )

        if m:
            return int(m.group(1))

    return None


def competencia_declarada(paginas):

    for pagina in paginas:

        texto = sem_acento(pagina["texto"])

        m = re.search(
            r"(?:competencia|referencia|mes de referencia)\s*:?\s*"
            r"(0?[1-9]|1[0-2])\s*[/\-.]\s*(\d{4})",
            texto
        )

        if m:
            return f"{int(m.group(1)):02d}/{m.group(2)}"

        m = re.search(
            r"(?:competencia|referencia|folha(?: de pagamento)?)"
            r"[^\n]{0,20}?\b(" + "|".join(_MESES) + r")\b"
            r"\s*(?:de\s*|/\s*)?(\d{4})",
            texto
        )

        if m:
            return f"{_MESES[m.group(1)]:02d}/{m.group(2)}"

    return None


# ----------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------

def _soma(registros):

    return sum(
        (r["valor"] for r in registros),
        Decimal("0.00")
    )


def ler(conteudo: bytes, valor_esperado=None):
    """Roda todas as estratégias e devolve a melhor leitura:
    {
      "funcionarios": [...], "rejeitados": [...],
      "estrategia": str, "valor_total_documento": Decimal|None,
      "quantidade_documento": int|None, "competencia": str|None,
      "tem_texto": bool, "bate_extrato": bool|None,
    }"""

    paginas = extrair_paginas(conteudo)

    tem_texto = any(p["texto"].strip() for p in paginas)

    total_doc = total_declarado(paginas)

    qtd_doc = quantidade_declarada(paginas)

    esperado = (
        Decimal(str(valor_esperado)).quantize(Decimal("0.01"))
        if valor_esperado is not None
        else None
    )

    candidatos = []

    for nome, estrategia in (
        ("ancora_cpf", estrategia_ancora_cpf),
        ("rotulos", estrategia_rotulos),
        ("linhas", estrategia_linhas),
    ):
        registros, rejeitados = estrategia(paginas)

        soma = _soma(registros)

        candidatos.append({
            "estrategia": nome,
            "funcionarios": registros,
            "rejeitados": rejeitados,
            "score": (
                bool(registros) and esperado is not None
                and abs(soma - esperado) <= TOLERANCIA_SOMA,

                bool(registros) and total_doc is not None
                and abs(soma - total_doc) <= Decimal("0.01"),

                bool(registros) and qtd_doc is not None
                and len(registros) == qtd_doc,

                # Preferência entre estratégias quando nada acima
                # desempata: âncora > rótulos > linhas.
                bool(registros),

                -[
                    "ancora_cpf", "rotulos", "linhas"
                ].index(nome),
            ),
        })

    melhor = max(candidatos, key=lambda c: c["score"])

    soma = _soma(melhor["funcionarios"])

    return {
        "funcionarios": melhor["funcionarios"],
        "rejeitados": melhor["rejeitados"],
        "estrategia": melhor["estrategia"],
        "valor_total_documento": total_doc,
        "quantidade_documento": qtd_doc,
        "competencia": competencia_declarada(paginas),
        "tem_texto": tem_texto,
        "bate_extrato": (
            abs(soma - esperado) <= TOLERANCIA_SOMA
            if esperado is not None and melhor["funcionarios"]
            else None
        ),
    }
