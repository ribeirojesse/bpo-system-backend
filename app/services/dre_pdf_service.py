import io

from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
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
CINZA_TEXTO = colors.HexColor("#37352f")
CINZA_CLARO = colors.HexColor("#9b9a97")
LINHA = colors.HexColor("#e9e9e7")
FUNDO_ALT = colors.HexColor("#f7f6f5")
VERDE = colors.HexColor("#0f7b6c")
VERMELHO = colors.HexColor("#e03e3e")
COR_PADRAO = "#4f46e5"


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
            textColor=CINZA_TEXTO,
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_LEFT,
        )

        subtitulo_style = ParagraphStyle(
            "DreSubtitulo",
            parent=styles["Normal"],
            textColor=CINZA_CLARO,
            fontName="Helvetica",
            fontSize=11,
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
            Paragraph(
                "Demonstração de Resultado (DRE)",
                titulo_style
            )
        )

        modo_label = {
            "CATEGORIA": "por categoria",
            "BANCO": "por conta bancária",
            "BANCO_CATEGORIA": "por conta bancária e categoria",
        }.get(dados["modo"], "")

        elementos.append(
            Paragraph(
                f"{dados['cliente_nome']} • Exercício {dados['ano']} • "
                f"Visão {modo_label} • Gerado em "
                f"{datetime.now().strftime('%d/%m/%Y')}",
                subtitulo_style,
            )
        )

        elementos.append(Spacer(1, 18))

        elementos.append(
            DrePdfService._cards_resumo(dados, largura)
        )

        elementos.append(Spacer(1, 22))

        if dados.get("saldos_contas"):

            elementos.append(
                Paragraph("Saldo em Contas Bancárias", secao_style)
            )

            elementos.append(
                DrePdfService._tabela_saldos(
                    dados["saldos_contas"], largura, cor_destaque
                )
            )

            elementos.append(Spacer(1, 22))

        elementos.append(Paragraph("Receitas", secao_style))

        elementos.append(
            DrePdfService._tabela_linhas(
                dados["linhas_receita"],
                dados["meses"],
                largura,
                cor_destaque,
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
            )
        )

        elementos.append(Spacer(1, 22))

        elementos.append(Paragraph("Resumo Mensal", secao_style))

        elementos.append(
            DrePdfService._tabela_resumo_mensal(dados, largura)
        )

        doc.build(elementos)

        return buffer.getvalue()

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

        dados_tabela = [[
            card("RECEITA TOTAL", dados["receita_anual"], "#0f7b6c"),
            card("DESPESA TOTAL", dados["despesa_anual"], "#e03e3e"),
            card("RESULTADO", dados["resultado_anual"], "#37352f"),
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
    def _tabela_saldos(saldos_contas, largura, cor_destaque):

        linhas = [["Banco", "Conta", "Saldo"]]

        total = 0

        for item in saldos_contas:

            linhas.append([
                item["banco"],
                item["conta"],
                brl(item["saldo"]),
            ])

            total += float(item["saldo"] or 0)

        linhas.append(["", "Total", brl(total)])

        return DrePdfService._tabela(
            linhas,
            [largura * 0.4, largura * 0.4, largura * 0.2],
            cor_destaque=cor_destaque,
            destacar_ultima_linha=True,
        )

    @staticmethod
    def _tabela_linhas(linhas, meses, largura, cor_destaque):

        cabecalho = ["Categoria"] + meses + ["Total"]

        dados_tabela = [cabecalho]

        for linha in linhas:
            dados_tabela.append(
                [linha["nome"]]
                + [brl(v) for v in linha["valores_mensais"]]
                + [brl(linha["total"])]
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
            dados_tabela, col_widths, cor_destaque=cor_destaque
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
                colors.HexColor("#eef2ff")
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
        destacar_ultima_linha=False
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

        if destacar_ultima_linha:

            estilo.append((
                "BACKGROUND", (0, -1), (-1, -1),
                colors.HexColor("#eef2ff")
            ))

            estilo.append((
                "FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"
            ))

        tabela.setStyle(TableStyle(estilo))

        return tabela
