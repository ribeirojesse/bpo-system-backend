from typing import Literal, Optional

from datetime import date

import uuid

from decimal import Decimal

from pydantic import BaseModel, Field


# Tetos de tamanho/valor aceitos na entrada (a resposta não usa estes).
_DESCRICAO = dict(min_length=1, max_length=500)
_VALOR = dict(gt=0, le=Decimal("9999999999.99"))
_COMPETENCIA = dict(max_length=20)
_OBSERVACAO = dict(max_length=2000)


class AccountsPayableCreateSchema(BaseModel):

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID] = None

    descricao: str = Field(**_DESCRICAO)

    valor: Decimal = Field(**_VALOR)

    vencimento: date

    # Data em que o pagamento efetivamente ocorreu. Toda conta a pagar já
    # nasce como PAGA (lançamento manual = pagamento já realizado) — se não
    # informada, o serviço usa a própria data de vencimento/lançamento.
    data_pagamento: Optional[date] = None

    competencia: Optional[str] = Field(None, **_COMPETENCIA)

    observacao: Optional[str] = Field(None, **_OBSERVACAO)


class AccountsPayableUpdateSchema(BaseModel):

    financial_contact_id: Optional[uuid.UUID] = None

    category_id: Optional[uuid.UUID] = None

    subcategory_id: Optional[uuid.UUID] = None

    descricao: Optional[str] = Field(None, **_DESCRICAO)

    valor: Optional[Decimal] = Field(None, **_VALOR)

    vencimento: Optional[date] = None

    data_pagamento: Optional[date] = None

    competencia: Optional[str] = Field(None, **_COMPETENCIA)

    # Só os status que o sistema realmente usa (ver dre_service e
    # due_reminders): qualquer outro valor deixaria a conta fora de todos
    # os relatórios.
    status: Optional[Literal["PENDENTE", "PAGO"]] = None

    observacao: Optional[str] = Field(None, **_OBSERVACAO)


class AccountsPayableResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: uuid.UUID

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID]

    descricao: str

    valor: Decimal

    vencimento: date

    data_pagamento: Optional[date]

    competencia: Optional[str]

    status: str

    observacao: Optional[str]

    class Config:
        from_attributes = True