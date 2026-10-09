import uuid

from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    ConfigDict,
    Field
)

from app.core.password_policy import SenhaForte, SenhaOpcional


class AdminUserCreateSchema(BaseModel):

    # Nome da empresa/carteira (vira o Tenant deste usuário).
    tenant_nome: str = Field(min_length=1, max_length=200)

    nome: str = Field(min_length=1, max_length=200)

    email: EmailStr

    password: SenhaForte


class AdminUserUpdateSchema(BaseModel):

    nome: Optional[str] = Field(None, min_length=1, max_length=200)

    email: Optional[EmailStr] = None

    # Opcional: só troca a senha se for enviada.
    password: SenhaOpcional = None

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
