from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.security import verify_password, create_access_token

from app.models.user import User

from app.schemas.auth import LoginSchema, RefreshTokenSchema

from app.dependencies.auth import get_current_user

from app.services.refresh_token_service import RefreshTokenService

router = APIRouter()


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
def login(data: LoginSchema, db: Session = Depends(get_db)):

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

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ============================================================
# REFRESH TOKEN
# ============================================================


@router.post("/refresh")
def refresh(data: RefreshTokenSchema, db: Session = Depends(get_db)):

    token = RefreshTokenService.validate(db, data.refresh_token)

    if not token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido"
        )

    user = token.user

    new_access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )

    new_refresh_token = RefreshTokenService.rotate(db, token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


# ============================================================
# LOGOUT
# ============================================================


@router.post("/logout")
def logout(data: RefreshTokenSchema, db: Session = Depends(get_db)):

    RefreshTokenService.revoke(db, data.refresh_token)

    return {"message": "Logout realizado"}


# ============================================================
# LOGOUT TODOS DISPOSITIVOS
# ============================================================


@router.post("/logout-all")
def logout_all(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):

    RefreshTokenService.revoke_all(db, current_user)

    return {"message": "Todos os dispositivos desconectados"}


# ============================================================
# CURRENT USER
# ============================================================


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):

    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role,
    }
