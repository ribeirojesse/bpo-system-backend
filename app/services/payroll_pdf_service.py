"""Leitura do comprovante de folha de pagamento (PDF ou imagem).

Ordem de tentativa:

1. **Leitura local, sem IA** (app/services/payroll_pdf_parser.py) — várias
   estratégias por posição na página (âncora no CPF + colunas do
   cabeçalho, blocos "Rótulo: valor", linha simples), escolhendo a que
   bate com o valor do extrato / total do documento. Se a soma bate com o
   extrato, para aqui: custo zero, sem mandar nada pra fora.
2. **IA (se ANTHROPIC_API_KEY estiver configurada)** — só quando a leitura
   local não fechou (layout muito diferente, PDF escaneado, foto). O
   arquivo vai inteiro pro Claude.
3. Sem IA (ou IA fora do ar): devolve a melhor leitura local, com avisos
   — a tela mostra tudo pra conferência antes de gravar.

Em qualquer caminho, o resultado passa por `limpar_funcionarios`, que
normaliza nomes/CPF/valores e descarta linhas inválidas.
"""

import base64
import logging
import re

from decimal import Decimal, InvalidOperation

from app.core.config import settings
from app.services import payroll_pdf_parser
from app.services.ai_client import AIClient, AIError


logger = logging.getLogger(__name__)


TIPOS_ACEITOS = {
    "application/pdf": "PDF",
    "image/png": "PNG",
    "image/jpeg": "JPG",
    "image/webp": "WEBP",
}


class PayrollExtractionError(Exception):
    """Não foi possível ler o arquivo (formato inválido, imagem sem IA,
    etc.). A mensagem é segura para mostrar ao usuário."""


_SYSTEM_PROMPT_FOLHA = """Você lê comprovantes bancários de pagamento de folha \
(pagamento de salários em lote) emitidos por bancos brasileiros e extrai a \
lista de pagamentos individuais. Cada banco usa um layout diferente \
(tabelas, blocos por funcionário, várias páginas, PDF escaneado, foto de \
tela); leia o documento como uma pessoa leria.

Regras:
- Um item por pagamento a um funcionário/favorecido.
- "valor" é o valor efetivamente creditado/pago a essa pessoa (líquido). \
Escreva com ponto decimal e sem separador de milhar, ex.: "3450.00".
- Ignore cabeçalhos, rodapés, dados da empresa pagadora, linhas de total/ \
subtotal, tarifas e autenticações.
- Se o documento indicar que um pagamento foi rejeitado, devolvido, \
cancelado ou não efetuado, NÃO inclua esse item e explique em "observacoes".
- "cpf": copie como aparece no documento (pode estar mascarado); null se \
não houver.
- "valor_total_documento": o total do lote declarado no documento, se \
existir; null se não houver.
- "competencia": no formato MM/AAAA, apenas se o documento informar \
explicitamente a competência/mês de referência; senão null.
- "banco": nome do banco emissor, se identificável.
- Se o arquivo não for um comprovante de pagamento de folha/salários, \
devolva "funcionarios" vazio e explique em "observacoes".
- Nunca invente nomes ou valores. Se um valor estiver ilegível, deixe o \
item de fora e cite em "observacoes"."""


_TOOL_FOLHA = {
    "name": "registrar_folha",
    "description": (
        "Registra os pagamentos individuais extraídos do comprovante "
        "de folha de pagamento."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "funcionarios": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nome": {"type": "string"},
                        "cpf": {"type": ["string", "null"]},
                        "valor": {
                            "type": "string",
                            "description": "Valor pago, ex.: 3450.00",
                        },
                    },
                    "required": ["nome", "valor"],
                },
            },
            "valor_total_documento": {"type": ["string", "null"]},
            "competencia": {"type": ["string", "null"]},
            "banco": {"type": ["string", "null"]},
            "observacoes": {"type": ["string", "null"]},
        },
        "required": ["funcionarios"],
    },
}


class PayrollPDFService:

    # ==================================================================
    # Utilidades
    # ==================================================================

    @staticmethod
    def detectar_tipo(conteudo: bytes):
        """Identifica o tipo real pelo conteúdo (assinatura do arquivo),
        não pela extensão/Content-Type enviados pelo navegador."""

        if conteudo.startswith(b"%PDF"):
            return "application/pdf"

        if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        if conteudo.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        if (
            conteudo[:4] == b"RIFF"
            and conteudo[8:12] == b"WEBP"
        ):
            return "image/webp"

        return None

    @staticmethod
    def parse_valor(valor):
        """Converte valor monetário em Decimal com 2 casas. Aceita número,
        "1234.56", "1.234,56", "R$ 1.234,56", "1,234.56". Devolve None se
        não der pra interpretar com segurança."""

        if valor is None:
            return None

        if isinstance(valor, (int, float, Decimal)):
            try:
                return Decimal(str(valor)).quantize(Decimal("0.01"))
            except InvalidOperation:
                return None

        texto = re.sub(r"[^\d,.\-]", "", str(valor))

        if not texto or not re.search(r"\d", texto):
            return None

        if "," in texto and "." in texto:
            # O separador que aparece por último é o decimal.
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")

        elif "," in texto:
            texto = texto.replace(".", "").replace(",", ".")

        elif texto.count(".") > 1:
            # "1.234.567" sem decimais → milhar.
            texto = texto.replace(".", "")

        try:
            return Decimal(texto).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None

    @staticmethod
    def normalizar_cpf(cpf):

        if not cpf:
            return None

        cpf = str(cpf).strip()

        digitos = re.sub(r"\D", "", cpf)

        if len(digitos) == 11 and cpf.replace(".", "").replace("-", "").isdigit():
            return (
                f"{digitos[:3]}.{digitos[3:6]}."
                f"{digitos[6:9]}-{digitos[9:]}"
            )

        # Mascarado ("***.456.789-**") ou formato estranho: guarda como
        # veio, limitado, só pra conferência.
        return cpf[:20] or None

    @staticmethod
    def normalizar_competencia(competencia):

        if not competencia:
            return None

        match = re.search(
            r"(0?[1-9]|1[0-2])\s*[/\-.]\s*(\d{4})",
            str(competencia)
        )

        if not match:
            return None

        return f"{int(match.group(1)):02d}/{match.group(2)}"

    @staticmethod
    def limpar_funcionarios(itens):
        """Valida e normaliza a lista (vinda da IA, do regex ou editada
        pelo usuário na tela). Cada item de saída:
        {"funcionario": str, "cpf": str|None, "valor": Decimal}.
        Devolve (itens_validos, avisos)."""

        validos = []
        avisos = []

        for item in itens or []:

            if not isinstance(item, dict):
                continue

            nome = (
                item.get("funcionario")
                or item.get("nome")
                or ""
            )

            nome = re.sub(r"\s+", " ", str(nome)).strip()[:150]

            valor = PayrollPDFService.parse_valor(
                item.get("valor")
            )

            if len(nome) < 2:
                avisos.append(
                    "Uma linha sem nome foi descartada."
                )
                continue

            if valor is None or valor <= 0:
                avisos.append(
                    f"Linha de \"{nome}\" descartada: valor inválido."
                )
                continue

            validos.append({
                "funcionario": nome,
                "cpf": PayrollPDFService.normalizar_cpf(
                    item.get("cpf")
                ),
                "valor": valor,
            })

        return validos, avisos

    # ==================================================================
    # Leitura local (sem IA)
    # ==================================================================

    @staticmethod
    def _ler_local(conteudo: bytes, valor_esperado):
        """Roda o parser local e monta o resultado no formato padrão.
        Devolve None se o PDF não abre."""

        try:
            leitura = payroll_pdf_parser.ler(conteudo, valor_esperado)
        except Exception as exc:
            logger.warning("Falha ao abrir PDF: %s", exc.__class__.__name__)
            return None

        funcionarios, avisos = PayrollPDFService.limpar_funcionarios(
            leitura["funcionarios"]
        )

        if leitura["rejeitados"]:
            nomes = ", ".join(
                r["funcionario"] for r in leitura["rejeitados"][:5]
            )
            avisos.append(
                f"{len(leitura['rejeitados'])} pagamento(s) marcado(s) "
                f"no documento como rejeitado/devolvido/cancelado "
                f"ficaram de fora: {nomes}."
            )

        if not leitura["tem_texto"]:
            avisos.append(
                "O PDF não tem texto selecionável (parece escaneado ou "
                "foto) — sem a IA não dá pra ler automaticamente."
            )

        elif not funcionarios:
            avisos.append(
                "Não reconhecemos o layout deste comprovante. Adicione "
                "as linhas manualmente ou peça ao banco o arquivo de "
                "retorno do lote."
            )

        qtd_doc = leitura["quantidade_documento"]

        if (
            funcionarios
            and qtd_doc is not None
            and qtd_doc != len(funcionarios)
        ):
            avisos.append(
                f"O documento informa {qtd_doc} pagamento(s), mas "
                f"{len(funcionarios)} foram lidos — confira a lista."
            )

        resultado = {
            "funcionarios": funcionarios,
            "metodo": "LOCAL",
            "avisos": avisos,
            "valor_total_documento": leitura["valor_total_documento"],
            "competencia_detectada": leitura["competencia"],
            "banco": None,
            "_bate_extrato": leitura["bate_extrato"],
        }

        PayrollPDFService._conferir_total(resultado)

        return resultado

    @staticmethod
    def _leitura_local_confiavel(resultado, valor_esperado):

        if not resultado or not resultado["funcionarios"]:
            return False

        if valor_esperado is not None:
            return bool(resultado["_bate_extrato"])

        total_doc = resultado["valor_total_documento"]

        if total_doc is None:
            return False

        soma = sum(
            (f["valor"] for f in resultado["funcionarios"]),
            Decimal("0.00")
        )

        return abs(soma - total_doc) <= Decimal("0.01")

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
            system=_SYSTEM_PROMPT_FOLHA,
            content=[
                bloco_arquivo,
                {
                    "type": "text",
                    "text": (
                        "Extraia os pagamentos individuais deste "
                        "comprovante de folha de pagamento."
                    ),
                },
            ],
            tool=_TOOL_FOLHA,
            max_tokens=12000,
        )

    @staticmethod
    def _ler_com_ia(conteudo, media_type):

        bruto = PayrollPDFService.extrair_com_ia(conteudo, media_type)

        funcionarios, avisos = PayrollPDFService.limpar_funcionarios(
            bruto.get("funcionarios")
        )

        observacoes = (bruto.get("observacoes") or "").strip()

        if observacoes:
            avisos.append(f"Observação da IA: {observacoes[:500]}")

        resultado = {
            "funcionarios": funcionarios,
            "metodo": "IA",
            "avisos": avisos,
            "valor_total_documento": PayrollPDFService.parse_valor(
                bruto.get("valor_total_documento")
            ),
            "competencia_detectada": (
                PayrollPDFService.normalizar_competencia(
                    bruto.get("competencia")
                )
            ),
            "banco": (bruto.get("banco") or "").strip()[:80] or None,
        }

        PayrollPDFService._conferir_total(resultado)

        return resultado

    # ==================================================================
    # Orquestração
    # ==================================================================

    @staticmethod
    def extrair(
        conteudo: bytes,
        media_type: str,
        valor_esperado=None
    ) -> dict:
        """Lê o arquivo e devolve:
        {
          "funcionarios": [{"funcionario", "cpf", "valor": Decimal}],
          "metodo": "LOCAL" | "IA",
          "avisos": [str],
          "valor_total_documento": Decimal | None,
          "competencia_detectada": "MM/AAAA" | None,
          "banco": str | None,
        }
        `valor_esperado` (valor da transação do extrato) ajuda a escolher
        a leitura certa e decide se vale chamar a IA."""

        if media_type not in TIPOS_ACEITOS:
            raise PayrollExtractionError(
                "Formato não suportado. Envie PDF, PNG, JPG ou WEBP."
            )

        local = None

        if media_type == "application/pdf":

            local = PayrollPDFService._ler_local(
                conteudo,
                valor_esperado
            )

            if PayrollPDFService._leitura_local_confiavel(
                local,
                valor_esperado
            ):
                local.pop("_bate_extrato", None)
                return local

        if AIClient.habilitado():

            try:
                resultado_ia = PayrollPDFService._ler_com_ia(
                    conteudo,
                    media_type
                )

                # Se a IA também não achou nada mas a leitura local achou
                # algo, fica com a local (mais avisos que nada).
                if resultado_ia["funcionarios"] or not (
                    local and local["funcionarios"]
                ):
                    return resultado_ia

            except AIError:

                if local is not None:
                    local["avisos"].insert(
                        0,
                        "A leitura com IA não está disponível agora — "
                        "usamos a leitura automática. Confira a lista "
                        "com atenção."
                    )

        if media_type != "application/pdf":
            raise PayrollExtractionError(
                "Leitura de imagem precisa da IA, que não está "
                "disponível agora. Envie o comprovante em PDF."
                if AIClient.habilitado()
                else "Envio de foto/imagem só funciona com a IA "
                "ativada. Envie o comprovante em PDF."
            )

        if local is None:
            raise PayrollExtractionError(
                "Não foi possível abrir o PDF (arquivo corrompido "
                "ou protegido por senha)."
            )

        local.pop("_bate_extrato", None)

        return local

    @staticmethod
    def _conferir_total(resultado):

        total_doc = resultado.get("valor_total_documento")

        if total_doc is None:
            return

        soma = sum(
            (f["valor"] for f in resultado["funcionarios"]),
            Decimal("0.00")
        )

        if resultado["funcionarios"] and abs(soma - total_doc) > Decimal("0.01"):
            resultado["avisos"].append(
                f"A soma dos funcionários (R$ {soma:.2f}) não bate com o "
                f"total informado no documento (R$ {total_doc:.2f}) — "
                "pode faltar ou sobrar alguma linha."
            )
