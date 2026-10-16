import io
import os

from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
    Image,
    KeepTogether,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT


# Paleta "estilo Notion": texto quase-preto (nunca preto puro), cinza
# neutro pra rótulos secundários, bordas bem claras, e UMA cor de
# destaque (a do template, ou o indigo já usado no resto da plataforma)
# usada com moderação — nunca blocos de cor saturada cobrindo a tabela
# inteira, ao contrário dos modelos de referência que inspiraram este
# relatório.
# Identidade Tower: preto, branco e grafite (ver landing.css). O nome do
# cliente é o título do documento — o relatório é dele, a Tower assina no
# topo e no rodapé.
TOWER_TINTA = colors.HexColor("#000000")
TOWER_GRAFITE = colors.HexColor("#3a3a3a")
TOWER_FUMACA = colors.HexColor("#5e5e5e")

MARCA_TOWER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "tower-marca.png",
)

ASSINATURA_TOWER = (
    "Tower — BPO e Consultoria Financeira · towerbpo.com"
)

CINZA_TEXTO = colors.HexColor("#37352f")
CINZA_CLARO = colors.HexColor("#9b9a97")
LINHA = colors.HexColor("#e9e9e7")
FUNDO_ALT = colors.HexColor("#f7f6f5")
VERDE = colors.HexColor("#0f7b6c")
VERMELHO = colors.HexColor("#e03e3e")
COR_PADRAO = "#111111"


def brl(valor):

    valor = float(valor or 0)

    texto = f"{valor:,.2f}"

    texto = (
        texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {texto}"


class DrePdfService:

    @staticmethod
    def gerar(dados: dict) -> bytes:

        cor_destaque = colors.HexColor(
            dados.get("cor_destaque") or COR_PADRAO
        )

        buffer = io.BytesIO()

        # Landscape A3 (não A4) de propósito — com 12 colunas de mês
        # mais categoria e total, A4 deixa os valores praticamente
        # colados uns nos outros. É a mesma escolha já feita no modelo
        # de referência genérico que inspirou este relatório.
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A3),
            leftMargin=32,
            rightMargin=32,
            topMargin=36,
            bottomMargin=32,
        )

        styles = getSampleStyleSheet()

        titulo_style = ParagraphStyle(
            "DreTitulo",
            parent=styles["Title"],
            textColor=TOWER_TINTA,
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=30,
            alignment=TA_LEFT,
            # Caixa alta com leve tracking lembra o Archivo Black da
            # identidade sem precisar embarcar a fonte no servidor.
            trackingAmount=0.6,
        )

        subtitulo_style = ParagraphStyle(
            "DreSubtitulo",
            parent=styles["Normal"],
            textColor=TOWER_FUMACA,
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
        )

        secao_style = ParagraphStyle(
            "DreSecao",
            parent=styles["Heading2"],
            textColor=CINZA_TEXTO,
            fontName="Helvetica-Bold",
            fontSize=13,
            spaceBefore=4,
            spaceAfter=8,
        )

        largura = doc.width

        elementos = []

        elementos.append(
            DrePdfService._cabecalho_marca(largura)
        )

        elementos.append(Spacer(1, 10))

        # O nome do cliente é o título: quem abre o PDF vê primeiro o
        # próprio nome, não o nome do relatório.
        elementos.append(
            Paragraph(
                (dados["cliente_nome"] or "").upper(),
                titulo_style,
            )
        )

        modo_label = {
            "CATEGORIA": "por categoria",
            "BANCO": "por conta bancária",
            "BANCO_CATEGORIA": "por conta bancária e categoria",
        }.get(dados["modo"], "")

        conta_txt = (
            f" · Conta {dados['conta_filtro']}"
            if dados.get("conta_filtro")
            else ""
        )

        meses_txt = (
            f" · Meses {dados['meses_filtro']}"
            if dados.get("meses_filtro")
            else ""
        )

        elementos.append(
            Paragraph(
                "Demonstração de Resultado (DRE) · Exercício "
                f"{dados['ano']}{conta_txt}{meses_txt} · Visão "
                f"{modo_label} · Gerado em "
                f"{datetime.now().strftime('%d/%m/%Y')}",
                subtitulo_style,
            )
        )

        elementos.append(Spacer(1, 18))

        elementos.append(
            DrePdfService._cards_resumo(dados, largura)
        )

        elementos.append(Spacer(1, 22))

        elementos.append(Paragraph("Receitas", secao_style))

        elementos.append(
            DrePdfService._tabela_linhas(
                dados["linhas_receita"],
                dados["meses"],
                largura,
                cor_destaque,
                dados.get("mostrar_subcategorias", False),
            )
        )

        elementos.append(Spacer(1, 22))

        elementos.append(Paragraph("Despesas", secao_style))

        elementos.append(
            DrePdfService._tabela_linhas(
                dados["linhas_despesa"],
                dados["meses"],
                largura,
                cor_destaque,
                dados.get("mostrar_subcategorias", False),
            )
        )

        elementos.append(Spacer(1, 22))

        # Resumo e título andam juntos: tabela curta quebrada no meio
        # da página fica com cara de erro.
        elementos.append(
            KeepTogether([
                Paragraph("Resumo Mensal", secao_style),
                DrePdfService._tabela_resumo_mensal(dados, largura),
            ])
        )

        doc.build(
            elementos,
            onFirstPage=DrePdfService._rodape,
            onLaterPages=DrePdfService._rodape,
        )

        return buffer.getvalue()

    @staticmethod
    def _cabecalho_marca(largura):
        """Marca da Tower à esquerda e a assinatura à direita, separadas
        da área do relatório por um fio preto."""

        assinatura_style = ParagraphStyle(
            "DreAssinatura",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=TOWER_GRAFITE,
            alignment=2,
            trackingAmount=1.2,
        )

        marca = ""

        if os.path.exists(MARCA_TOWER):
            # 137x168 no arquivo: mantém a proporção da marca.
            marca = Image(MARCA_TOWER, width=19.5, height=24)

        tabela = Table(
            [[
                marca,
                Paragraph(
                    ASSINATURA_TOWER.upper(),
                    assinatura_style
                ),
            ]],
            colWidths=[30, largura - 30],
        )

        tabela.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 1.2, TOWER_TINTA),
        ]))

        return tabela

    @staticmethod
    def _rodape(canvas, doc):
        """Assinatura e número da página no pé de cada folha."""

        canvas.saveState()

        canvas.setFont("Helvetica", 8)

        canvas.setFillColor(TOWER_FUMACA)

        canvas.drawString(
            doc.leftMargin,
            18,
            ASSINATURA_TOWER
        )

        canvas.drawRightString(
            doc.pagesize[0] - doc.rightMargin,
            18,
            f"Página {canvas.getPageNumber()}"
        )

        canvas.restoreState()

    @staticmethod
    def _cards_resumo(dados, largura):

        # Rótulo e valor são dois flowables separados (não um único
        # Paragraph com <br/>) porque o leading de um Paragraph não se
        # ajusta automaticamente ao tamanho da maior fonte inline — com
        # <br/> misturando size=9 e size=17 na mesma linha, o valor
        # grande acabava sobrepondo visualmente o rótulo acima dele.
        # Como flowables distintos, cada um usa o leading do seu próprio
        # ParagraphStyle e o espaçamento fica sempre correto.
        rotulo_style = ParagraphStyle(
            "DreCardRotulo",
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=CINZA_CLARO,
            spaceAfter=4,
        )

        def valor_style(cor_hex):
            return ParagraphStyle(
                "DreCardValor",
                fontName="Helvetica-Bold",
                fontSize=17,
                leading=21,
                textColor=colors.HexColor(cor_hex),
            )

        def card(rotulo, valor, cor_hex):
            return [
                Paragraph(rotulo, rotulo_style),
                Paragraph(brl(valor), valor_style(cor_hex)),
            ]

        # Com meses filtrados os totais são do recorte, não do ano —
        # o rótulo precisa dizer isso.
        sufixo = (
            " DO PERÍODO"
            if dados.get("meses_filtro")
            else " DO EXERCÍCIO"
        )

        dados_tabela = [[
            card(
                f"RECEITA{sufixo}",
                dados["receita_anual"],
                "#0f7b6c"
            ),
            card(
                f"DESPESA{sufixo}",
                dados["despesa_anual"],
                "#e03e3e"
            ),
            card("RESULTADO", dados["resultado_anual"], "#111111"),
        ]]

        tabela = Table(dados_tabela, colWidths=[largura / 3] * 3)

        tabela.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, LINHA),
            ("INNERGRID", (0, 0), (-1, -1), 0.75, LINHA),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ]))

        return tabela

    @staticmethod
    def _tabela_linhas(
        linhas,
        meses,
        largura,
        cor_destaque,
        mostrar_subcategorias=False
    ):

        cabecalho = ["Categoria"] + meses + ["Total"]

        dados_tabela = [cabecalho]

        # Índices das linhas de subcategoria, pra estilizar depois com um
        # tom mais claro (a tabela do reportlab é uma matriz; o recuo no
        # nome é o que mostra a hierarquia).
        linhas_filhas = []

        for linha in linhas:

            dados_tabela.append(
                [linha["nome"]]
                + [brl(v) for v in linha["valores_mensais"]]
                + [brl(linha["total"])]
            )

            if not mostrar_subcategorias:
                continue

            for sub in linha.get("subcategorias") or []:

                linhas_filhas.append(len(dados_tabela))

                dados_tabela.append(
                    [f"     {sub['nome']}"]
                    + [brl(v) for v in sub["valores_mensais"]]
                    + [brl(sub["total"])]
                )

        if not linhas:
            dados_tabela.append(
                ["Nenhum lançamento no período"]
                + [""] * (len(meses) + 1)
            )

        num_meses = len(meses)

        col_widths = (
            [largura * 0.18]
            + [(largura * 0.70) / num_meses] * num_meses
            + [largura * 0.12]
        )

        return DrePdfService._tabela(
            dados_tabela,
            col_widths,
            cor_destaque=cor_destaque,
            linhas_filhas=linhas_filhas,
        )

    @staticmethod
    def _tabela_resumo_mensal(dados, largura):

        meses = dados["meses"]

        linhas = [
            [""] + meses,
            ["Receitas"] + [brl(v) for v in dados["totais_receita"]],
            ["Despesas"] + [brl(v) for v in dados["totais_despesa"]],
            ["Resultado"] + [brl(v) for v in dados["totais_resultado"]],
        ]

        col_widths = (
            [largura * 0.14]
            + [(largura * 0.86) / len(meses)] * len(meses)
        )

        tabela = Table(linhas, colWidths=col_widths)

        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO_ALT),
            ("TEXTCOLOR", (0, 0), (-1, 0), CINZA_TEXTO),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            (
                "BACKGROUND",
                (0, 3), (-1, 3),
                colors.HexColor("#f1f1f1")
            ),
            ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, LINHA),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        return tabela

    @staticmethod
    def _tabela(
        dados_tabela,
        col_widths,
        cor_destaque=None,
        destacar_ultima_linha=False,
        linhas_filhas=None
    ):

        tabela = Table(
            dados_tabela,
            colWidths=col_widths,
            repeatRows=1,
        )

        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO_ALT),
            (
                "TEXTCOLOR", (0, 0), (-1, 0),
                cor_destaque or CINZA_TEXTO
            ),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, LINHA),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            (
                "ROWBACKGROUNDS",
                (0, 1), (-1, -1),
                [colors.white, FUNDO_ALT],
            ),
        ]

        # Subcategoria: mesma linha, tinta mais clara e sem zebra —
        # lida como detalhe da categoria logo acima.
        for indice in (linhas_filhas or []):

            estilo.append((
                "TEXTCOLOR", (0, indice), (-1, indice), TOWER_FUMACA
            ))

            estilo.append((
                "FONTSIZE", (0, indice), (-1, indice), 8
            ))

        if destacar_ultima_linha:

            estilo.append((
                "BACKGROUND", (0, -1), (-1, -1),
                colors.HexColor("#f1f1f1")
            ))

            estilo.append((
                "FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"
            ))

        tabela.setStyle(TableStyle(estilo))

        return tabela
