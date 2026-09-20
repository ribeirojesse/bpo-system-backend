from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(
    title="BPO Financeiro API"
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