from pydantic import BaseModel, EmailStr


class RegisterSchema(BaseModel):

    tenant_nome: str

    nome: str

    email: EmailStr

    password: str


class LoginSchema(BaseModel):

    email: EmailStr

    password: str


class TokenSchema(BaseModel):

    access_token: str

    token_type: str = "bearer"