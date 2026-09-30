from pydantic import BaseModel, EmailStr


class LoginSchema(BaseModel):

    email: EmailStr

    password: str


class TokenSchema(BaseModel):

    access_token: str

    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):

    refresh_token: str


# ------------------------------------------------------------------
# App mobile — os tokens viajam no corpo (JSON), não em cookie, e o app
# guarda no armazenamento seguro do aparelho (Keychain / Keystore).
# ------------------------------------------------------------------

class MobileTokenResponseSchema(BaseModel):

    access_token: str

    refresh_token: str

    token_type: str = "bearer"

    expires_in: int
