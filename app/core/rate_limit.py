"""Limite de requisições (rate limiting) em memória, sem dependências novas.

Janela deslizante por chave (IP + nome do limite). Serve para frear força
bruta no login, abuso das rotas de IA (que geram custo na Anthropic) e
uploads em massa.

Limitações conhecidas (aceitas de propósito):
- O contador vive na memória de cada processo. Com 1 worker do uvicorn (o
  caso atual) o limite é exato; com N workers, o limite efetivo é N vezes
  maior. O nginx tem uma segunda camada (limit_req) que é global.
- Reiniciar a API zera os contadores.
"""

import threading
import time

from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings


_lock = threading.Lock()

_hits: dict[str, deque] = defaultdict(deque)

# Evita crescimento infinito do dicionário: a cada N chamadas, descarta
# chaves cujas tentativas já saíram de qualquer janela razoável.
_CLEANUP_EVERY = 500
_calls = 0
_MAX_WINDOW_SECONDS = 3600


def client_ip(request: Request) -> str:
    """IP do cliente.

    Em produção a API só é alcançável através do nginx, que repassa o IP
    real em X-Real-IP; fora de produção esse cabeçalho poderia ser forjado
    por qualquer um, então ele é ignorado.
    """

    if settings.ENVIRONMENT == "production":

        real_ip = request.headers.get("x-real-ip")

        if real_ip:
            return real_ip.strip()

    return request.client.host if request.client else "desconhecido"


def _limpar(now: float) -> None:

    for key in list(_hits.keys()):

        fila = _hits[key]

        while fila and now - fila[0] > _MAX_WINDOW_SECONDS:
            fila.popleft()

        if not fila:
            del _hits[key]


def rate_limit(nome: str, max_requests: int, window_seconds: int):
    """Cria uma dependência do FastAPI que limita `max_requests` chamadas
    por `window_seconds` segundos, por IP.

    Uso: `dependencies=[Depends(rate_limit("login", 10, 60))]`.
    """

    def _dependency(request: Request) -> None:

        global _calls

        now = time.monotonic()

        key = f"{nome}:{client_ip(request)}"

        with _lock:

            _calls += 1

            if _calls % _CLEANUP_EVERY == 0:
                _limpar(now)

            fila = _hits[key]

            while fila and now - fila[0] > window_seconds:
                fila.popleft()

            if len(fila) >= max_requests:

                retry_after = max(
                    1,
                    int(window_seconds - (now - fila[0]))
                )

                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Muitas tentativas. "
                        "Aguarde um pouco e tente novamente."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )

            fila.append(now)

    return _dependency
