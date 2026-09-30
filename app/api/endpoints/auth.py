from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from sqlalchemy.orm import Session

from app.core.config import settings

from app.core.database import get_db

from app.core.security import verify_password, create_access_token

from app.models.user import User

from app.schemas.auth import (
    LoginSchema,
    RefreshTokenSchema,
    MobileTokenResponseSchema,
)

from app.dependencies.auth import get_current_user

from app.services.refresh_token_service import RefreshTokenService

router = APIRouter()


# ============================================================
# COOKIES DE SESSÃO
# ============================================================
#
# access_token e refresh_token viajam em cookies httpOnly (não em JSON
# no corpo da resposta) — um script rodando na página (ex: via uma falha
# de XSS) não consegue ler esses valores, só o navegador, que os reenvia
# sozinho em toda requisição pra api.towerbpo.com.

_COOKIE_KWARGS = dict(
    httponly=True,
    secure=settings.ENVIRONMENT == "production",  # exige HTTPS em produção
    samesite="lax",
    domain=settings.COOKIE_DOMAIN or None,
    path="/",
)


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
):

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_KWARGS,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **_COOKIE_KWARGS,
    )


def _clear_auth_cookies(response: Response):

    response.delete_cookie(
        "access_token",
        path="/",
        domain=settings.COOKIE_DOMAIN or None,
    )

    response.delete_cookie(
        "refresh_token",
        path="/",
        domain=settings.COOKIE_DOMAIN or None,
    )


# ============================================================
# REGISTER (removido)
# ============================================================
#
# Existia aqui um POST /register público: qualquer um podia se
# auto-provisionar um tenant + usuário sem autenticação nenhuma. Isso foi
# removido — a criação de usuários agora exige um SUPER_ADMIN autenticado
# e vive em POST /admin/users (ver app/api/endpoints/admin_user.py e
# app/services/admin_user_service.py), que faz a mesma coisa por baixo
# (cria Tenant + User) só que protegida.


# ============================================================
# LOGIN
# ============================================================


@router.post("/login")
def login(data: LoginSchema, response: Response, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:

        raise HTTPException(status_code=400, detail="Email ou senha inválidos")

    if not verify_password(data.password, user.senha_hash):

        raise HTTPException(status_code=400, detail="Email ou senha inválidos")

    if not user.ativo:

        raise HTTPException(status_code=403, detail="Usuário desativado")

    access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )

    refresh_token = RefreshTokenService.create(db, user)

    # Manutenção oportunista: aproveita o login para descartar
    # refresh tokens já expirados (não há agendador/cron no projeto).
    RefreshTokenService.cleanup(db)

    _set_auth_cookies(response, access_token, refresh_token)

    return {"message": "Login realizado"}


# ============================================================
# REFRESH TOKEN
# ============================================================


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):

    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente"
        )

    token = RefreshTokenService.validate(db, refresh_token)

    if not token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido"
        )

    user = token.user

    new_access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )

    new_refresh_token = RefreshTokenService.rotate(db, token)

    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return {"message": "Token renovado"}


# ============================================================
# LOGOUT
# ============================================================


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):

    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        RefreshTokenService.revoke(db, refresh_token)

    _clear_auth_cookies(response)

    return {"message": "Logout realizado"}


# ============================================================
# LOGOUT TODOS DISPOSITIVOS
# ============================================================


@router.post("/logout-all")
def logout_all(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    RefreshTokenService.revoke_all(db, current_user)

    _clear_auth_cookies(response)

    return {"message": "Todos os dispositivos desconectados"}


# ============================================================
# CURRENT USER
# ============================================================


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):

    client = current_user.client

    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role,
        # Campos extras (usados pelo app mobile no cabeçalho) — só
        # preenchidos pro role CLIENTE; o frontend web simplesmente ignora.
        "client_id": current_user.client_id,
        "client_nome": (
            (client.nome_fantasia or client.razao_social)
            if client else None
        ),
    }


# ============================================================
# APP MOBILE (React Native)
# ============================================================
#
# Mesmo fluxo de login/refresh/logout do web, mas os tokens vão e voltam
# no corpo JSON em vez de cookie httpOnly — num app nativo não existe
# navegador pra guardar cookie, e o app guarda os tokens no
# armazenamento seguro do aparelho (Keychain no iOS, Keystore no
# Android, via expo-secure-store). As rotas protegidas aceitam o token
# no header "Authorization: Bearer ..." (ver dependencies/auth.py).
#
# Refresh token com rotação (o antigo é revogado a cada uso), igual ao web.


def _autenticar(db: Session, data: LoginSchema) -> User:

    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.senha_hash):

        raise HTTPException(status_code=400, detail="Email ou senha inválidos")

    if not user.ativo:

        raise HTTPException(status_code=403, detail="Usuário desativado")

    return user


def _emitir_tokens_mobile(db: Session, user: User) -> dict:

    access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )

    refresh_token = RefreshTokenService.create(db, user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/mobile/login", response_model=MobileTokenResponseSchema)
def mobile_login(data: LoginSchema, db: Session = Depends(get_db)):

    user = _autenticar(db, data)

    RefreshTokenService.cleanup(db)

    return _emitir_tokens_mobile(db, user)


@router.post("/mobile/refresh", response_model=MobileTokenResponseSchema)
def mobile_refresh(data: RefreshTokenSchema, db: Session = Depends(get_db)):

    token = RefreshTokenService.validate(db, data.refresh_token)

    if not token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido"
        )

    user = token.user

    if not user.ativo:

        raise HTTPException(status_code=403, detail="Usuário desativado")

    new_access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )

    new_refresh_token = RefreshTokenService.rotate(db, token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/mobile/logout")
def mobile_logout(data: RefreshTokenSchema, db: Session = Depends(get_db)):

    RefreshTokenService.revoke(db, data.refresh_token)

    return {"message": "Logout realizado"}
