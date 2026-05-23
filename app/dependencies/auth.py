from jose import jwt, JWTError

from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/routes/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido"
    )

    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise credentials_exception

    return user