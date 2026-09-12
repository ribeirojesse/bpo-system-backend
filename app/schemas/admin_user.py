import uuid

from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    ConfigDict
)


class AdminUserCreateSchema(BaseModel):

    # Nome da empresa/carteira (vira o Tenant deste usuário).
    tenant_nome: str

    nome: str

    email: EmailStr

    password: str


class AdminUserUpdateSchema(BaseModel):

    nome: Optional[str] = None

    email: Optional[EmailStr] = None

    # Opcional: só troca a senha se for enviada.
    password: Optional[str] = None

    ativo: Optional[bool] = None


class AdminUserResponseSchema(BaseModel):

    id: uuid.UUID

    nome: str

    email: str

    ativo: bool

    tenant_id: Optional[uuid.UUID] = None

    tenant_nome: Optional[str] = None

    clientes_count: int = 0

    model_config = ConfigDict(
        from_attributes=True
    )
