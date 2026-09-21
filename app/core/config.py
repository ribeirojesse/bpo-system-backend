from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str

    SECRET_KEY: str

    ALGORITHM: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int

    REFRESH_TOKEN_EXPIRE_DAYS: int

    # "development" (padrão, preserva o comportamento atual) ou
    # "production" — usado para decidir coisas como o --reload do
    # uvicorn no Dockerfile.
    ENVIRONMENT: str = "development"

    # Lista de origens permitidas pelo CORS, separadas por vírgula.
    # Mantém o valor atual como padrão para não quebrar nada que já
    # funciona; em produção, configurar via variável de ambiente.
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Domínio usado no cookie de sessão (access_token/refresh_token).
    # Vazio (padrão) = cookie "host-only", funciona sozinho em localhost.
    # Em produção, use ".towerbpo.com" (com o ponto na frente) — assim o
    # cookie emitido por api.towerbpo.com também é enviado em requisições
    # pra api.towerbpo.com vindas de páginas em towerbpo.com (mesmo
    # domínio raiz = cookie tratado como "mesmo site" pelo navegador).
    COOKIE_DOMAIN: str = ""

    class Config:
        env_file = ".env"

    @property
    def allowed_origins_list(self) -> list[str]:

        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
