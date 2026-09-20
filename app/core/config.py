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
