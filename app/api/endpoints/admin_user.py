from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import require_role

from app.models.user import User

from app.schemas.admin_user import (
    AdminUserCreateSchema,
    AdminUserUpdateSchema,
    AdminUserResponseSchema
)

from app.services.admin_user_service import AdminUserService


router = APIRouter()


# Todas as rotas aqui são restritas a SUPER_ADMIN. É o painel que cria
# os USERS (role ADMIN), cada um dono da própria carteira de clients.
# Substitui o antigo POST /auth/register, que era público.


@router.post(
    "/",
    response_model=AdminUserResponseSchema
)
def create_user(
    data: AdminUserCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("SUPER_ADMIN"))
):

    return AdminUserService.create_user(db, data)


@router.get(
    "/",
    response_model=list[AdminUserResponseSchema]
)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("SUPER_ADMIN"))
):

    return AdminUserService.list_users(db)


@router.put(
    "/{user_id}",
    response_model=AdminUserResponseSchema
)
def update_user(
    user_id: str,
    data: AdminUserUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("SUPER_ADMIN"))
):

    return AdminUserService.update_user(db, user_id, data)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("SUPER_ADMIN"))
):

    return AdminUserService.delete_user(db, user_id)
