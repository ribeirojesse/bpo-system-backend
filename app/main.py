from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router

app = FastAPI(
    title="BPO Financeiro API"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
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