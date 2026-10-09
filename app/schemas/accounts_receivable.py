from typing import Literal, Optional

from datetime import date

from decimal import Decimal

from pydantic import BaseModel, Field

import uuid


# Tetos de tamanho/valor aceitos na entrada (a resposta não usa estes).
_DESCRICAO = dict(min_length=1, max_length=500)
_VALOR = dict(gt=0, le=Decimal("9999999999.99"))
_COMPETENCIA = dict(max_length=20)
_OBSERVACAO = dict(max_length=2000)


class AccountsReceivableCreateSchema(BaseModel):

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID] = None

    descricao: str = Field(**_DESCRICAO)

    valor: Decimal = Field(**_VALOR)

    vencimento: date

    # Data em que o recebimento efetivamente ocorreu. Toda conta a receber
    # já nasce como RECEBIDA (lançamento manual = recebimento já realizado)
    # — se não informada, o serviço usa a própria data de vencimento/
    # lançamento.
    data_recebimento: Optional[date] = None

    competencia: Optional[str] = Field(None, **_COMPETENCIA)

    observacao: Optional[str] = Field(None, **_OBSERVACAO)


class AccountsReceivableUpdateSchema(BaseModel):

    # Contato/categoria/subcategoria não são editáveis aqui (o schema
    # nunca os aceitou), então não há referência a revalidar no update.
    descricao: Optional[str] = Field(None, **_DESCRICAO)

    valor: Optional[Decimal] = Field(None, **_VALOR)

    vencimento: Optional[date] = None

    data_recebimento: Optional[date] = None

    competencia: Optional[str] = Field(None, **_COMPETENCIA)

    status: Optional[Literal["PENDENTE", "RECEBIDO"]] = None

    observacao: Optional[str] = Field(None, **_OBSERVACAO)


class AccountsReceivableResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID]

    descricao: str

    valor: Decimal

    vencimento: date

    data_recebimento: Optional[date]

    competencia: Optional[str]

    status: str

    observacao: Optional[str]

    class Config:
        from_attributes = True