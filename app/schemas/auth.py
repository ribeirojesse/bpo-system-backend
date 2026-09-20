from pydantic import BaseModel, EmailStr


class LoginSchema(BaseModel):

    email: EmailStr

    password: str


class TokenSchema(BaseModel):

    access_token: str

    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):

    refresh_token: str
