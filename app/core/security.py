from datetime import datetime, timedelta, UTC
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ============================================================
# PASSWORD
# ============================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# ============================================================
# ACCESS TOKEN
# ============================================================

def create_access_token(
    data: dict[str, Any]
) -> str:

    payload = data.copy()

    expire = (
        datetime.now(UTC)
        + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload.update({
        "type": "access",
        "exp": expire
    })

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


# ============================================================
# REFRESH TOKEN
# ============================================================

def create_refresh_token(
    data: dict[str, Any]
) -> tuple[str, datetime]:

    expire = (
        datetime.now(UTC)
        + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    payload = data.copy()

    payload.update({
        "type": "refresh",
        "exp": expire
    })

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return token, expire


# ============================================================
# GENERIC DECODER
# ============================================================

def decode_token(
    token: str
) -> dict:

    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )


# ============================================================
# TOKEN TYPE
# ============================================================

def is_access_token(
    payload: dict
) -> bool:

    return payload.get("type") == "access"


def is_refresh_token(
    payload: dict
) -> bool:

    return payload.get("type") == "refresh"