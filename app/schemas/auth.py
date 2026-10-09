from pydantic import BaseModel, EmailStr, Field


class LoginSchema(BaseModel):

    email: EmailStr

    # Sem mínimo aqui de propósito (senhas antigas continuam entrando);
    # o teto evita mandar megabytes de texto para o bcrypt.
    password: str = Field(min_length=1, max_length=128)


class TokenSchema(BaseModel):

    access_token: str

    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):

    refresh_token: str = Field(min_length=1, max_length=2048)


# ------------------------------------------------------------------
# App mobile — os tokens viajam no corpo (JSON), não em cookie, e o app
# guarda no armazenamento seguro do aparelho (Keychain / Keystore).
# ------------------------------------------------------------------

class MobileTokenResponseSchema(BaseModel):

    access_token: str

    refresh_token: str

    token_type: str = "bearer"

    expires_in: int
