"""Cliente fino para a API do Claude (Anthropic).

Centraliza em um lugar só:
  - se a IA está habilitada (ANTHROPIC_API_KEY no .env);
  - criação preguiçosa do cliente (só instancia na primeira chamada, pra
    não quebrar o boot da API quando a chave não existe);
  - chamada com "tool use" forçado, que é o jeito mais confiável de
    receber JSON estruturado do modelo — a resposta já vem validada
    contra o input_schema da ferramenta, sem precisar "caçar" JSON no
    meio de texto livre;
  - tradução de qualquer erro da SDK para AIError, que o resto do
    sistema trata como "IA indisponível, segue sem ela".

Nada aqui grava no banco nem decide nada sozinho: quem chama sempre
valida o que voltou antes de usar (IDs, valores, etc.).
"""

import logging

from app.core.config import settings


logger = logging.getLogger(__name__)


class AIError(Exception):
    """Falha ao falar com a IA (sem chave, timeout, erro da API, resposta
    fora do formato). Quem chama decide o fallback."""


class AIClient:

    _client = None

    @staticmethod
    def habilitado() -> bool:

        return bool(
            (settings.ANTHROPIC_API_KEY or "").strip()
        )

    @classmethod
    def _get_client(cls):

        if not cls.habilitado():
            raise AIError(
                "IA não configurada (ANTHROPIC_API_KEY vazia)"
            )

        if cls._client is None:

            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover
                raise AIError(
                    "Pacote 'anthropic' não instalado — "
                    "rode pip install -r requirements.txt"
                ) from exc

            cls._client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY.strip(),
                timeout=settings.AI_TIMEOUT_SECONDS,
                # A SDK já refaz sozinha em erro de rede/429/5xx, com
                # backoff exponencial.
                max_retries=2,
            )

        return cls._client

    @classmethod
    def chamar_ferramenta(
        cls,
        *,
        model: str,
        system: str,
        content: list,
        tool: dict,
        max_tokens: int = 4096,
    ) -> dict:
        """Envia `content` (lista de blocos: texto, documento, imagem) e
        obriga o modelo a responder chamando `tool`. Devolve o `input` da
        chamada de ferramenta (um dict já no formato do input_schema)."""

        client = cls._get_client()

        try:

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        # Instruções fixas: se passarem do tamanho mínimo
                        # de cache, as próximas chamadas pagam ~10% do
                        # preço por esse trecho. Abaixo do mínimo, é
                        # simplesmente ignorado.
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[tool],
                tool_choice={
                    "type": "tool",
                    "name": tool["name"],
                },
                messages=[
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
            )

        except Exception as exc:
            # anthropic.APIError e derivados (timeout, conexão, 4xx/5xx).
            # Nunca loga o conteúdo enviado (pode ter dado pessoal).
            logger.warning(
                "Falha na chamada à IA (%s): %s",
                model,
                exc.__class__.__name__,
            )
            raise AIError(
                "Não foi possível falar com a IA agora"
            ) from exc

        usage = getattr(response, "usage", None)

        if usage is not None:
            logger.info(
                "IA %s — tokens entrada=%s saída=%s cache_lido=%s",
                model,
                getattr(usage, "input_tokens", "?"),
                getattr(usage, "output_tokens", "?"),
                getattr(usage, "cache_read_input_tokens", 0),
            )

        if getattr(response, "stop_reason", None) == "max_tokens":
            raise AIError(
                "Resposta da IA foi cortada (limite de tokens)"
            )

        for block in response.content:

            if (
                getattr(block, "type", None) == "tool_use"
                and block.name == tool["name"]
            ):
                if not isinstance(block.input, dict):
                    break

                return block.input

        raise AIError(
            "A IA não devolveu a resposta no formato esperado"
        )
