from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings

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

@app.get("/")
def root():
    return {
        "message": "API ONLINE"
    }