from jose import jwt, JWTError

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status
)

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import is_access_token

from app.models.user import User


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido"
    )

    # O access token agora vem num cookie httpOnly (não mais no header
    # Authorization) — setado pelo /auth/login, inacessível a JavaScript
    # no navegador (proteção contra roubo via XSS).
    token = request.cookies.get("access_token")

    if not token:
        raise credentials_exception

    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        # Garante que apenas access tokens autenticam rotas protegidas
        # (um refresh token não pode ser usado como Bearer token).
        if not is_access_token(payload):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise credentials_exception

    return user


def require_role(*roles: str):
    """
    Dependency factory para restringir uma rota a um ou mais roles.

    Uso: current_user: User = Depends(require_role("SUPER_ADMIN"))
    """

    def dependency(
        current_user: User = Depends(get_current_user)
    ):

        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado para este perfil de usuário"
            )

        return current_user

    return dependency
