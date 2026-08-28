from datetime import datetime, UTC

from jose import JWTError

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.models.user import User

from app.core.security import (
    create_refresh_token,
    decode_token,
    is_refresh_token
)


class RefreshTokenService:

    @staticmethod
    def create(
        db: Session,
        user: User
    ):

        token, expires_at = create_refresh_token(
            {
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id)
            }
        )

        refresh = RefreshToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at
        )

        db.add(refresh)

        db.commit()

        return token

    @staticmethod
    def validate(
        db: Session,
        token: str
    ):

        try:

            payload = decode_token(token)

            if not is_refresh_token(payload):
                return None

        except JWTError:
            return None

        refresh = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == token
            )
            .first()
        )

        if refresh is None:
            return None

        if refresh.revoked:
            return None

        if refresh.expires_at < datetime.now(UTC):
            return None

        return refresh

    @staticmethod
    def revoke(
        db: Session,
        token: str
    ):

        refresh = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == token
            )
            .first()
        )

        if refresh:

            refresh.revoked = True

            db.commit()

    @staticmethod
    def revoke_all(
        db: Session,
        user: User
    ):

        (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked == False
            )
            .update(
                {
                    RefreshToken.revoked: True
                }
            )
        )

        db.commit()

    @staticmethod
    def rotate(
        db: Session,
        refresh: RefreshToken
    ):

        refresh.revoked = True

        db.flush()

        return RefreshTokenService.create(
            db,
            refresh.user
        )

    @staticmethod
    def cleanup(
        db: Session
    ):

        (
            db.query(RefreshToken)
            .filter(
                RefreshToken.expires_at <
                datetime.now(UTC)
            )
            .delete()
        )

        db.commit()