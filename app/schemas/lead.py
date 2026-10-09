import re
import uuid

from datetime import datetime

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Parâmetros de origem aceitos no campo "atribuicao" — qualquer outra
# chave é descartada (o endpoint é público, então nada de guardar JSON
# arbitrário enviado por qualquer um).
ATRIBUICAO_PERMITIDA = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "gbraid",
    "wbraid",
    "fbclid",
    "referrer",
    "landing",
}

LeadStatus = Literal["NOVO", "EM_CONTATO", "CONVERTIDO", "DESCARTADO"]


class LeadCreateSchema(BaseModel):

    nome: str = Field(min_length=2, max_length=120)

    empresa: str = Field(min_length=1, max_length=160)

    whatsapp: str = Field(min_length=10, max_length=30)

    volume: Optional[str] = Field(None, max_length=40)

    mensagem: Optional[str] = Field(None, max_length=1000)

    pagina: Optional[str] = Field(None, max_length=200)

    atribuicao: Optional[dict[str, str]] = None

    # Honeypot: campo escondido no formulário. Pessoa de verdade não vê
    # nem preenche; robô que preenche tudo é ignorado em silêncio.
    website: Optional[str] = Field(None, max_length=200)

    @field_validator("nome", "empresa")
    @classmethod
    def _strip(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError("Campo obrigatório")

        return value

    @field_validator("whatsapp")
    @classmethod
    def _whatsapp(cls, value: str) -> str:

        digitos = re.sub(r"\D", "", value)

        # Aceita com ou sem o 55 do Brasil na frente.
        if digitos.startswith("55") and len(digitos) in (12, 13):
            digitos = digitos[2:]

        if len(digitos) not in (10, 11):
            raise ValueError("Informe o WhatsApp com DDD")

        return digitos

    @field_validator("atribuicao")
    @classmethod
    def _atribuicao(cls, value):

        if not value:
            return None

        limpo = {
            chave: str(valor)[:255]
            for chave, valor in value.items()
            if chave in ATRIBUICAO_PERMITIDA and valor
        }

        return limpo or None


class LeadStatusUpdateSchema(BaseModel):

    status: LeadStatus


class LeadResponseSchema(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    nome: str

    empresa: str

    whatsapp: str

    volume: Optional[str] = None

    mensagem: Optional[str] = None

    pagina: Optional[str] = None

    utm_source: Optional[str] = None

    utm_medium: Optional[str] = None

    utm_campaign: Optional[str] = None

    atribuicao: Optional[dict] = None

    status: str

    created_at: datetime
