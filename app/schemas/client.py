from uuid import UUID

from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr
)


class ClientCreateSchema(BaseModel):

    razao_social: str
    nome_fantasia: Optional[str] = None
    cnpj: str

    email: Optional[EmailStr] = None
    telefone: Optional[str] = None


class ClientUpdateSchema(BaseModel):

    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None

    email: Optional[EmailStr] = None
    telefone: Optional[str] = None


class ClientResponseSchema(BaseModel):

    id: UUID

    razao_social: str
    nome_fantasia: Optional[str]
    cnpj: str

    email: Optional[str]
    telefone: Optional[str]

    class Config:
        from_attributes = True


# Acesso do CLIENTE ao portal (login travado a este client, ver
# ck_users_role_scope). Todo client já tem um login criado automaticamente
# pela migration b1c4a9d7e2f0 — este schema serve pra o ADMIN enxergar
# qual é o e-mail atual e, se quiser, trocar e-mail/senha.

class ClientPortalAccessResponseSchema(BaseModel):

    has_access: bool
    email: Optional[str] = None


class ClientPortalAccessUpdateSchema(BaseModel):

    email: Optional[EmailStr] = None
    password: Optional[str] = None
