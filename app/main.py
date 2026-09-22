import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)

# Em produção, desliga a documentação interativa (/docs, /redoc) e o
# schema bruto (/openapi.json) — não bloqueia nada por si só, mas evita
# deixar público um mapa detalhado de todos os endpoints, parâmetros e
# formatos de request/response da API pra qualquer um que ache a URL.
_is_production = settings.ENVIRONMENT == "production"

app = FastAPI(
    title="BPO Financeiro API",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# CORS
# Origens vêm de settings.ALLOWED_ORIGINS (variável de ambiente
# ALLOWED_ORIGINS, separada por vírgula). O padrão preserva o
# comportamento atual (só localhost:5173) até ser configurado.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(
    api_router,
    prefix="/api/routes"
)


@app.exception_handler(Exception)
async def erro_nao_tratado(request: Request, exc: Exception):
    """Rede de segurança pra qualquer exceção que escape de um
    endpoint sem tratamento específico (ex.: um erro de serialização
    ao salvar no banco).

    Sem isso, a exceção sobe até o ServerErrorMiddleware do próprio
    Starlette — que fica FORA do CORSMiddleware na pilha de
    middlewares — e a resposta de erro 500 sai sem o cabeçalho
    Access-Control-Allow-Origin. No navegador isso aparece como "CORS
    Missing Allow Origin", escondendo completamente o erro real (o
    DevTools nem mostra a mensagem de erro do backend, só a falha de
    CORS) — foi exatamente isso que mascarou o bug real em
    DreService.update_template.

    Registrando o handler aqui, a exceção é capturada pelo
    ExceptionMiddleware do Starlette, que fica DENTRO do
    CORSMiddleware — a resposta de erro passa pelo CORS normalmente,
    e o erro completo (com stack trace) vai pro log do servidor em vez
    de simplesmente sumir."""

    logger.exception(
        "Erro não tratado em %s %s",
        request.method,
        request.url.path
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor"
        }
    )


@app.get("/")
def root():
    return {
        "message": "API ONLINE"
    }