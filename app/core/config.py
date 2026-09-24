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

    # ------------------------------------------------------------------
    # IA (API do Claude / Anthropic)
    # ------------------------------------------------------------------
    # Sem chave configurada, tudo que usa IA fica desligado e o sistema
    # continua funcionando como antes (heurística de conciliação e leitura
    # de PDF por regex). NUNCA commitar a chave — só no .env.
    ANTHROPIC_API_KEY: str = ""

    # Modelo usado pra sugerir conciliações (tarefa de texto curta, muitas
    # chamadas): o Haiku é rápido e barato e dá conta.
    AI_MODEL_CONCILIACAO: str = "claude-haiku-4-5-20251001"

    # Modelo usado pra ler documentos (PDF/imagem de folha de pagamento).
    # Leitura de tabela em layout variável de banco pra banco se beneficia
    # de um modelo mais forte; são poucas chamadas por mês.
    AI_MODEL_DOCUMENTOS: str = "claude-sonnet-5"

    # Tempo máximo de espera por resposta da API (segundos). Fica abaixo
    # do proxy_read_timeout padrão do nginx (60s).
    AI_TIMEOUT_SECONDS: int = 50

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
