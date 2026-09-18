import uuid

from datetime import date

from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict
)


class ClosingScheduleCreateSchema(BaseModel):

    client_id: Optional[uuid.UUID] = None

    titulo: str

    descricao: Optional[str] = None

    competencia: Optional[str] = None

    data_vencimento: date

    dias_lembrete: Optional[int] = 3


class ClosingScheduleUpdateSchema(BaseModel):

    client_id: Optional[uuid.UUID] = None

    titulo: Optional[str] = None

    descricao: Optional[str] = None

    competencia: Optional[str] = None

    data_vencimento: Optional[date] = None

    dias_lembrete: Optional[int] = None

    # Expostos aqui para permitir tanto "marcar como concluído" quanto
    # "reabrir" via um único PUT genérico (mesmo padrão de outras telas
    # do sistema, ex: reabrir conciliação).
    status: Optional[str] = None

    data_conclusao: Optional[date] = None


class ClosingScheduleResponseSchema(BaseModel):

    id: uuid.UUID

    client_id: Optional[uuid.UUID] = None

    titulo: str

    descricao: Optional[str] = None

    competencia: Optional[str] = None

    data_vencimento: date

    dias_lembrete: int

    status: str

    data_conclusao: Optional[date] = None

    model_config = ConfigDict(
        from_attributes=True
    )
