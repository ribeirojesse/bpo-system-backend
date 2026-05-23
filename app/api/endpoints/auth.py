from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)

from app.models.tenant import Tenant
from app.models.user import User

from app.schemas.auth import (
    RegisterSchema,
    LoginSchema
)

from app.dependencies.auth import get_current_user


router = APIRouter()


@router.post("/register")
def register(
    data: RegisterSchema,
    db: Session = Depends(get_db)
):

    user_exists = db.query(User).filter(
        User.email == data.email
    ).first()

    if user_exists:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado"
        )

    tenant = Tenant(
        nome=data.tenant_nome,
        email=data.email
    )

    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        nome=data.nome,
        email=data.email,
        senha_hash=hash_password(data.password)
    )

    db.add(user)

    db.commit()

    return {
        "message": "Usuário criado"
    }


@router.post("/login")
def login(
    data: LoginSchema,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email ou senha inválidos"
        )

    if not verify_password(
        data.password,
        user.senha_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Email ou senha inválidos"
        )

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id)
    })

    return {
        "access_token": token
    }


@router.get("/me")
def me(
    current_user: User = Depends(get_current_user)
):

    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id
    }