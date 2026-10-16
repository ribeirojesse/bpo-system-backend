"""Testes da importação das planilhas do sistema antigo.

Rodam sem banco e sem a aplicação de pé: testam só a conversão de cada
linha da planilha no que vai virar lançamento (datas, valores,
competência, contato padrão, nomes repetidos com acento diferente) e a
identidade que torna a importação segura de repetir.

    # dentro do container da API
    python tests/test_importar_legado.py

    # ou, se tiver pytest instalado
    pytest tests/test_importar_legado.py -v
"""

import os
import sys

from datetime import date
from decimal import Decimal


# O script vive em scripts/ e importa modelos da app; aqui só
# precisamos das funções puras, então carregamos o arquivo direto.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def _carregar_funcoes():
    """Lê scripts/importar_legado.py e executa apenas as funções puras,
    sem tocar nos imports da aplicação (que exigiriam banco)."""

    import ast
    import hashlib
    import textwrap
    import unicodedata

    from datetime import datetime
    from decimal import InvalidOperation

    caminho = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        "importar_legado.py",
    )

    codigo = open(caminho, encoding="utf-8").read()

    espaco = {
        "hashlib": hashlib,
        "unicodedata": unicodedata,
        "datetime": datetime,
        "Decimal": Decimal,
        "InvalidOperation": InvalidOperation,
    }

    puras = {
        "normalizar",
        "parse_data",
        "parse_valor",
        "marca_da_linha",
        "preparar_linha",
        "resumo_por_mes",
        "resumo_por_categoria",
        "ordem_competencia",
    }

    arvore = ast.parse(codigo)

    # Constantes do módulo que as funções usam.
    for no in arvore.body:

        if isinstance(no, ast.Assign):

            alvo = no.targets[0]

            if (
                isinstance(alvo, ast.Name)
                and alvo.id in ("CONTATO_PADRAO", "LIMITE_VALOR")
            ):
                exec(
                    ast.get_source_segment(codigo, no),
                    espaco
                )

    for no in arvore.body:

        if isinstance(no, ast.FunctionDef) and no.name in puras:
            exec(
                textwrap.dedent(
                    ast.get_source_segment(codigo, no)
                ),
                espaco
            )

    return espaco


F = _carregar_funcoes()


def linha(
    numero=2,
    contato="SANEPAR",
    data="08/01/2025",
    descricao="PGTO CONTA AGUA",
    valor=392.71,
    conta="BANCO BRASIL 61439-4",
    categoria="AGUA E SANEAMENTO",
):
    """Monta uma linha no formato que `ler_planilha` devolve."""

    return (numero, contato, data, descricao, valor, conta, categoria)


# ----------------------------------------------------------------------
# Datas
# ----------------------------------------------------------------------

def test_data_do_sistema_antigo_vira_date():

    dados, problema = F["preparar_linha"]("pagar", linha())

    assert problema is None
    assert dados["data"] == date(2025, 1, 8)


def test_competencia_e_o_mes_da_data():

    dados, _ = F["preparar_linha"](
        "pagar", linha(data="31/12/2025")
    )

    assert dados["competencia"] == "12/2025"


def test_data_em_outros_formatos():

    assert F["parse_data"]("2025-01-08") == date(2025, 1, 8)
    assert F["parse_data"]("08/01/25") == date(2025, 1, 8)
    assert F["parse_data"](date(2025, 1, 8)) == date(2025, 1, 8)


def test_linha_sem_data_e_recusada():

    dados, problema = F["preparar_linha"](
        "pagar", linha(data=None)
    )

    assert dados is None
    assert "data inválida" in problema


# ----------------------------------------------------------------------
# Valores
# ----------------------------------------------------------------------

def test_valor_vira_decimal_com_dois_digitos():

    dados, _ = F["preparar_linha"]("pagar", linha(valor=136.39))

    assert dados["valor"] == Decimal("136.39")
    assert isinstance(dados["valor"], Decimal)


def test_valor_em_texto_brasileiro():

    assert F["parse_valor"]("1.234,56") == Decimal("1234.56")
    assert F["parse_valor"]("R$ 281.716,95") == Decimal("281716.95")


def test_valor_zero_fica_de_fora():
    """As 7 linhas de valor zero da planilha de pagar não viram
    lançamento — zero não é conta a pagar."""

    dados, problema = F["preparar_linha"]("pagar", linha(valor=0))

    assert dados is None
    assert "valor inválido" in problema


def test_valor_acima_do_limite_da_coluna_e_recusado():
    """A coluna no banco é Numeric(10,2): acima disso o INSERT
    estouraria no meio da importação."""

    dados, problema = F["preparar_linha"](
        "pagar", linha(valor=123456789.01)
    )

    assert dados is None
    assert "limite" in problema


# ----------------------------------------------------------------------
# Contato, categoria e descrição
# ----------------------------------------------------------------------

def test_linha_sem_contato_vai_para_nao_informado():

    dados, _ = F["preparar_linha"]("pagar", linha(contato=None))

    assert dados["contato"] == "NAO INFORMADO"


def test_descricao_vazia_herda_a_categoria():

    dados, _ = F["preparar_linha"](
        "pagar", linha(descricao="   ", categoria="TARIFA BANCARIA")
    )

    assert dados["descricao"] == "TARIFA BANCARIA"


def test_nomes_iguais_com_acento_ou_caixa_diferente_sao_o_mesmo():
    """É o que evita criar "Doação" e "DOACAO" como duas categorias."""

    assert F["normalizar"]("Doação") == F["normalizar"]("DOACAO")
    assert F["normalizar"]("  Sanepar ") == "SANEPAR"


def test_conta_bancaria_e_preservada():

    dados, _ = F["preparar_linha"]("pagar", linha())

    assert dados["conta"] == "BANCO BRASIL 61439-4"


# ----------------------------------------------------------------------
# Identidade da linha (rodar duas vezes não duplica)
# ----------------------------------------------------------------------

def test_mesma_linha_gera_sempre_a_mesma_marca():

    primeira, _ = F["preparar_linha"]("pagar", linha())

    segunda, _ = F["preparar_linha"]("pagar", linha())

    assert primeira["marca"] == segunda["marca"]


def test_linhas_identicas_em_posicoes_diferentes_sao_lancamentos_diferentes():
    """Duas contas de água iguais no mesmo dia são dois pagamentos:
    as duas precisam entrar."""

    primeira, _ = F["preparar_linha"]("pagar", linha(numero=10))

    segunda, _ = F["preparar_linha"]("pagar", linha(numero=11))

    assert primeira["marca"] != segunda["marca"]


def test_pagar_e_receber_nao_se_confundem():

    pagar, _ = F["preparar_linha"]("pagar", linha())

    receber, _ = F["preparar_linha"]("receber", linha())

    assert pagar["marca"] != receber["marca"]


def test_valor_diferente_muda_a_marca():

    original, _ = F["preparar_linha"]("pagar", linha(valor=100))

    corrigida, _ = F["preparar_linha"]("pagar", linha(valor=101))

    assert original["marca"] != corrigida["marca"]


# ----------------------------------------------------------------------
# Resumos usados na conferência
# ----------------------------------------------------------------------

def test_resumo_por_mes_soma_certo():

    preparadas = [
        F["preparar_linha"]("pagar", linha(numero=2, valor=100))[0],
        F["preparar_linha"]("pagar", linha(numero=3, valor=50))[0],
        F["preparar_linha"](
            "pagar", linha(numero=4, data="05/02/2025", valor=25)
        )[0],
    ]

    por_mes = F["resumo_por_mes"](preparadas)

    assert por_mes["01/2025"] == (2, Decimal("150.00"))
    assert por_mes["02/2025"] == (1, Decimal("25.00"))


def test_competencias_ordenam_por_ano_e_mes():

    competencias = ["12/2025", "01/2026", "02/2025"]

    assert sorted(
        competencias, key=F["ordem_competencia"]
    ) == ["02/2025", "12/2025", "01/2026"]


def test_resumo_por_categoria_junta_variacoes_do_nome():

    preparadas = [
        F["preparar_linha"](
            "receber", linha(numero=2, categoria="Doação", valor=100)
        )[0],
        F["preparar_linha"](
            "receber", linha(numero=3, categoria="DOACAO", valor=40)
        )[0],
    ]

    por_categoria = F["resumo_por_categoria"](preparadas)

    assert len(por_categoria) == 1

    quantidade, soma, _nome = list(por_categoria.values())[0]

    assert (quantidade, soma) == (2, Decimal("140.00"))


# ----------------------------------------------------------------------
# Execução sem pytest
# ----------------------------------------------------------------------

def _rodar_sozinho():

    testes = [
        (nome, funcao)
        for nome, funcao in sorted(globals().items())
        if nome.startswith("test_") and callable(funcao)
    ]

    falhas = []

    for nome, funcao in testes:

        try:
            funcao()
            print(f"  ok    {nome}")

        except AssertionError as erro:
            falhas.append((nome, erro))
            print(f"  FALHA {nome}: {erro}")

        except Exception as erro:  # erro no próprio teste
            falhas.append((nome, erro))
            print(f"  ERRO  {nome}: {erro.__class__.__name__}: {erro}")

    print()
    print(
        f"{len(testes) - len(falhas)} de {len(testes)} testes passaram."
    )

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(_rodar_sozinho())
