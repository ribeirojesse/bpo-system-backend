"""Leitura da fatura de cartão de crédito (PDF ou imagem).

Mesma ordem de tentativa da folha de pagamento
(app/services/payroll_pdf_service.py):

1. **Leitura local, sem IA** (app/services/card_invoice_parser.py) — uma
   linha por lançamento, reconhecendo data no começo e valor no fim.
   Se a soma dos itens bate com o pagamento do extrato ou com o total
   declarado na fatura, para aqui: custo zero, sem mandar nada pra fora.
2. **IA (se ANTHROPIC_API_KEY estiver configurada)** — só quando a
   leitura local não fechou (layout diferente, fatura escaneada, foto).
3. Sem IA (ou IA fora do ar): devolve a melhor leitura local, com
   avisos — a tela mostra tudo pra conferência antes de gravar.

Em qualquer caminho o resultado passa por `limpar_itens`, que normaliza
descrição/valor/data/parcela e descarta linha inválida.
"""

import base64
import logging
import re

from datetime import date
from decimal import Decimal

from app.core.config import settings
from app.services import card_invoice_parser
from app.services.ai_client import AIClient, AIError
from app.services.payroll_pdf_service import PayrollPDFService


logger = logging.getLogger(__name__)


TIPOS_ACEITOS = {
    "application/pdf": "PDF",
    "image/png": "PNG",
    "image/jpeg": "JPG",
    "image/webp": "WEBP",
}


# Diferença tolerada ao decidir se a leitura local pode ser aceita sem
# IA. A tolerância do fechamento com o extrato é outra, e fica no
# CardInvoiceService.
TOLERANCIA_LEITURA = Decimal("0.01")


class CardInvoiceExtractionError(Exception):
    """Não foi possível ler o arquivo (formato inválido, imagem sem IA,
    PDF protegido). A mensagem é segura para mostrar ao usuário."""


_SYSTEM_PROMPT_FATURA = """Você lê faturas de cartão de crédito de bancos \
brasileiros e extrai a lista de lançamentos. Cada banco usa um layout \
diferente (uma tabela só, seções por portador/cartão, várias páginas, PDF \
escaneado, foto de tela); leia o documento como uma pessoa leria.

Regras:
- Um item por lançamento da fatura: compras, parcelas, anuidade, IOF, \
juros, seguros, estornos e créditos.
- "valor": com ponto decimal, sem separador de milhar, ex.: "345.90". \
Use valor NEGATIVO para o que reduz a fatura (estorno, devolução, \
desconto, cashback, pagamento da fatura anterior), ex.: "-50.00".
- Em compra internacional, use o valor em reais cobrado na fatura, não o \
valor em moeda estrangeira.
- "data": data do lançamento no formato DD/MM/AAAA. Se a fatura mostrar \
só dia e mês, devolva DD/MM e não invente o ano.
- "descricao": o estabelecimento/descrição como aparece na fatura.
- "parcela": "03/10" quando a linha indicar compra parcelada; senão null.
- "cartao": final do cartão (4 dígitos) ou nome do portador da seção, \
quando a fatura separar; senão null.
- NÃO inclua linhas de total, subtotal, limite, pagamento mínimo, saldo \
de faturas futuras, avisos, telefones e endereços.
- "total_fatura": o total a pagar declarado na fatura, se existir.
- "vencimento": vencimento da fatura em DD/MM/AAAA, se existir.
- "banco": nome do banco/emissor, se identificável.
- Se o arquivo não for uma fatura de cartão de crédito, devolva "itens" \
vazio e explique em "observacoes".
- Nunca invente valores. Se um valor estiver ilegível, deixe o item de \
fora e cite em "observacoes"."""


_TOOL_FATURA = {
    "name": "registrar_fatura",
    "description": (
        "Registra os lançamentos extraídos da fatura de cartão de "
        "crédito."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "itens": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "data": {"type": ["string", "null"]},
                        "descricao": {"type": "string"},
                        "valor": {
                            "type": "string",
                            "description": (
                                "Valor em reais, negativo para "
                                "crédito/estorno, ex.: 345.90"
                            ),
                        },
                        "parcela": {"type": ["string", "null"]},
                        "cartao": {"type": ["string", "null"]},
                    },
                    "required": ["descricao", "valor"],
                },
            },
            "total_fatura": {"type": ["string", "null"]},
            "vencimento": {"type": ["string", "null"]},
            "banco": {"type": ["string", "null"]},
            "observacoes": {"type": ["string", "null"]},
        },
        "required": ["itens"],
    },
}


_RE_DATA_TEXTO = re.compile(
    r"^\s*(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\s*$"
)

# "AAAA-MM-DD" — formato que o <input type="date"> da tela devolve.
_RE_DATA_ISO = re.compile(
    r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$"
)


class CardInvoicePDFService:

    # ==================================================================
    # Utilidades
    # ==================================================================

    @staticmethod
    def detectar_tipo(conteudo: bytes):
        """Identifica o tipo real pelo conteúdo do arquivo (mesma
        checagem da folha)."""

        return PayrollPDFService.detectar_tipo(conteudo)

    @staticmethod
    def parse_valor(valor):

        return PayrollPDFService.parse_valor(valor)

    @staticmethod
    def normalizar_competencia(competencia):

        return PayrollPDFService.normalizar_competencia(competencia)

    @staticmethod
    def _data_do_item(item, referencia=None):
        """Devolve `date` ou None. Aceita o que vem do parser local
        (dia/mes/ano), da IA ("DD/MM/AAAA" ou "DD/MM") e da tela
        ("AAAA-MM-DD").

        Sem ano no documento, usa o ano da `referencia` (data do
        pagamento no extrato); se o mês do lançamento é posterior ao da
        referência, assume o ano anterior — compra de dezembro numa
        fatura paga em janeiro."""

        dia = item.get("dia")

        mes = item.get("mes")

        ano = item.get("ano")

        if dia is None or mes is None:

            bruto = item.get("data") or item.get("data_compra")

            if isinstance(bruto, date):
                return bruto

            texto = str(bruto or "").strip()

            if not texto:
                return None

            iso = _RE_DATA_ISO.match(texto)

            if iso:
                ano, mes, dia = (
                    int(iso.group(1)),
                    int(iso.group(2)),
                    int(iso.group(3)),
                )
            else:

                match = _RE_DATA_TEXTO.match(texto)

                if not match:
                    return None

                dia = int(match.group(1))

                mes = int(match.group(2))

                ano = match.group(3)

                if ano:
                    ano = int(ano)
                    if ano < 100:
                        ano += 2000

        dia = int(dia)

        mes = int(mes)

        if not (1 <= dia <= 31 and 1 <= mes <= 12):
            return None

        if not ano:

            if referencia is None:
                return None

            ano = referencia.year

            if mes > referencia.month:
                ano -= 1

        try:
            return date(int(ano), mes, dia)
        except ValueError:
            return None

    @staticmethod
    def limpar_itens(itens, referencia=None):
        """Valida e normaliza a lista (do parser local, da IA ou editada
        na tela). Cada item de saída:
        {"data": date|None, "descricao": str, "valor": Decimal,
         "parcela": str|None, "cartao": str|None}.
        Devolve (itens_validos, avisos)."""

        validos = []

        avisos = []

        for item in itens or []:

            if not isinstance(item, dict):
                continue

            descricao = re.sub(
                r"\s+",
                " ",
                str(item.get("descricao") or "")
            ).strip()[:200]

            valor = CardInvoicePDFService.parse_valor(
                item.get("valor")
            )

            if len(descricao) < 2:
                avisos.append(
                    "Uma linha sem descrição foi descartada."
                )
                continue

            if valor is None or valor == 0:
                avisos.append(
                    f"Linha \"{descricao[:40]}\" descartada: "
                    "valor inválido."
                )
                continue

            parcela = str(item.get("parcela") or "").strip()[:10]

            cartao = str(item.get("cartao") or "").strip()[:40]

            validos.append({
                "data": CardInvoicePDFService._data_do_item(
                    item,
                    referencia
                ),
                "descricao": descricao,
                "valor": valor,
                "parcela": parcela or None,
                "cartao": cartao or None,
            })

        return validos, avisos

    @staticmethod
    def identificar(conteudo: bytes, media_type: str):
        """Lê só os identificadores da fatura (banco e finais de
        cartão/conta), sem itens e sem IA. Barato: serve pra conferir, na
        hora de gravar, se a fatura é mesmo a do cartão daquela
        transação. Em imagem não há o que ler sem IA — devolve vazio."""

        if media_type != "application/pdf":
            return {"banco": None, "finais": []}

        try:
            leitura = card_invoice_parser.ler(conteudo)
        except Exception:
            return {"banco": None, "finais": []}

        return {
            "banco": leitura.get("banco"),
            "finais": leitura.get("finais") or [],
        }

    @staticmethod
    def _soma(itens):

        return sum(
            (item["valor"] for item in itens),
            Decimal("0.00")
        )

    # ==================================================================
    # Leitura local (sem IA)
    # ==================================================================

    @staticmethod
    def _ler_local(conteudo: bytes, referencia=None):
        """Roda o parser local e monta o resultado no formato padrão.
        Devolve None se o PDF não abre."""

        try:
            leitura = card_invoice_parser.ler(conteudo)
        except Exception as exc:
            logger.warning(
                "Falha ao abrir PDF da fatura: %s",
                exc.__class__.__name__
            )
            return None

        itens, avisos = CardInvoicePDFService.limpar_itens(
            leitura["itens"],
            referencia
        )

        if not leitura["tem_texto"]:
            avisos.append(
                "O PDF não tem texto selecionável (parece escaneado ou "
                "foto) — sem a IA não dá pra ler automaticamente."
            )

        elif not itens:
            avisos.append(
                "Não reconhecemos o layout desta fatura. Confira os "
                "itens manualmente ou envie o PDF original do banco."
            )

        elif leitura["ignoradas"]:
            avisos.append(
                f"{leitura['ignoradas']} linha(s) com data não "
                "entraram na lista — confira se falta algum item."
            )

        vencimento = None

        if leitura["vencimento"]:

            dia, mes, ano = leitura["vencimento"]

            try:
                vencimento = date(ano, mes, dia)
            except (TypeError, ValueError):
                vencimento = None

        return {
            "itens": itens,
            "metodo": "LOCAL",
            "avisos": avisos,
            "total_documento": leitura["total_documento"],
            "vencimento": vencimento,
            "banco": leitura["banco"],
        }

    @staticmethod
    def _leitura_local_confiavel(resultado, valor_esperado):
        """Aceita a leitura local sem chamar a IA quando a soma fecha
        com o pagamento do extrato ou com o total declarado na fatura."""

        if not resultado or not resultado["itens"]:
            return False

        soma = CardInvoicePDFService._soma(resultado["itens"])

        if valor_esperado is not None:

            esperado = Decimal(
                str(valor_esperado)
            ).quantize(Decimal("0.01"))

            if abs(soma - esperado) <= TOLERANCIA_LEITURA:
                return True

        total_doc = resultado["total_documento"]

        return (
            total_doc is not None
            and abs(soma - total_doc) <= TOLERANCIA_LEITURA
        )

    # ==================================================================
    # IA
    # ==================================================================

    @staticmethod
    def extrair_com_ia(conteudo: bytes, media_type: str) -> dict:

        dados_b64 = base64.standard_b64encode(conteudo).decode("ascii")

        if media_type == "application/pdf":
            bloco_arquivo = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": dados_b64,
                },
            }
        else:
            bloco_arquivo = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": dados_b64,
                },
            }

        return AIClient.chamar_ferramenta(
            model=settings.AI_MODEL_DOCUMENTOS,
            system=_SYSTEM_PROMPT_FATURA,
            content=[
                bloco_arquivo,
                {
                    "type": "text",
                    "text": (
                        "Extraia os lançamentos desta fatura de "
                        "cartão de crédito."
                    ),
                },
            ],
            tool=_TOOL_FATURA,
            max_tokens=16000,
        )

    @staticmethod
    def _ler_com_ia(conteudo, media_type, referencia=None):

        bruto = CardInvoicePDFService.extrair_com_ia(
            conteudo,
            media_type
        )

        itens, avisos = CardInvoicePDFService.limpar_itens(
            bruto.get("itens"),
            referencia
        )

        observacoes = (bruto.get("observacoes") or "").strip()

        if observacoes:
            avisos.append(f"Observação da IA: {observacoes[:500]}")

        vencimento = CardInvoicePDFService._data_do_item(
            {"data": bruto.get("vencimento")},
            referencia
        )

        return {
            "itens": itens,
            "metodo": "IA",
            "avisos": avisos,
            "total_documento": CardInvoicePDFService.parse_valor(
                bruto.get("total_fatura")
            ),
            "vencimento": vencimento,
            "banco": (bruto.get("banco") or "").strip()[:80] or None,
        }

    # ==================================================================
    # Orquestração
    # ==================================================================

    @staticmethod
    def extrair(
        conteudo: bytes,
        media_type: str,
        valor_esperado=None,
        referencia=None
    ) -> dict:
        """Lê o arquivo e devolve:
        {
          "itens": [{"data", "descricao", "valor", "parcela",
                     "cartao"}],
          "metodo": "LOCAL" | "IA",
          "avisos": [str],
          "total_documento": Decimal | None,
          "vencimento": date | None,
          "banco": str | None,
        }
        `valor_esperado` (valor pago no extrato) decide se vale chamar a
        IA; `referencia` (data do pagamento) completa o ano das datas
        que a fatura mostra só como dia/mês."""

        if media_type not in TIPOS_ACEITOS:
            raise CardInvoiceExtractionError(
                "Formato não suportado. Envie PDF, PNG, JPG ou WEBP."
            )

        local = None

        if media_type == "application/pdf":

            local = CardInvoicePDFService._ler_local(
                conteudo,
                referencia
            )

            if CardInvoicePDFService._leitura_local_confiavel(
                local,
                valor_esperado
            ):
                return local

        if AIClient.habilitado():

            try:
                resultado_ia = CardInvoicePDFService._ler_com_ia(
                    conteudo,
                    media_type,
                    referencia
                )

                # Se a IA também não achou nada mas a leitura local
                # achou algo, fica com a local.
                if resultado_ia["itens"] or not (
                    local and local["itens"]
                ):
                    return resultado_ia

            except AIError:

                if local is not None:
                    local["avisos"].insert(
                        0,
                        "A leitura com IA não está disponível agora — "
                        "usamos a leitura automática. Confira os itens "
                        "com atenção."
                    )

        if media_type != "application/pdf":
            raise CardInvoiceExtractionError(
                "Leitura de imagem precisa da IA, que não está "
                "disponível agora. Envie a fatura em PDF."
                if AIClient.habilitado()
                else "Envio de foto/imagem só funciona com a IA "
                "ativada. Envie a fatura em PDF."
            )

        if local is None:
            raise CardInvoiceExtractionError(
                "Não foi possível abrir o PDF (arquivo corrompido ou "
                "protegido por senha)."
            )

        return local
