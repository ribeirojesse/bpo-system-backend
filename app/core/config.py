from pydantic import model_validator

from pydantic_settings import BaseSettings


# Valores de exemplo/placeholder que jamais podem assinar tokens em
# produção.
_SECRETS_PROIBIDOS = {
    "changeme",
    "secret",
    "secretkey",
    "sua_chave_secreta",
    "your-secret-key",
}


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

    # ------------------------------------------------------------------
    # PUSH NOTIFICATIONS (app mobile, via Expo Push Service)
    # ------------------------------------------------------------------
    # Opcional: só é necessário se "Enhanced Security for Push
    # Notifications" estiver ligado no projeto em expo.dev. Sem isso o
    # envio funciona normalmente.
    EXPO_ACCESS_TOKEN: str = ""

    # Quantos dias antes do vencimento o job diário de lembretes avisa
    # o cliente das contas a pagar (ver app/jobs/due_reminders.py).
    PUSH_DIAS_AVISO_VENCIMENTO: int = 1

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def _exigir_secret_forte_em_producao(self):
        """Em produção a API se recusa a subir com uma SECRET_KEY curta ou
        de exemplo — quem souber a chave consegue forjar o token de
        qualquer usuário. Em desenvolvimento nada muda."""

        if self.ENVIRONMENT == "production":

            chave = self.SECRET_KEY.strip()

            if len(chave) < 32 or chave.lower() in _SECRETS_PROIBIDOS:
                raise ValueError(
                    "SECRET_KEY fraca para produção: use pelo menos 32 "
                    "caracteres aleatórios (ex.: openssl rand -hex 32)"
                )

        return self

    @property
    def allowed_origins_list(self) -> list[str]:

        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
