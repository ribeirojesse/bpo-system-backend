from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    get_current_user
)

from app.models.user import User

from app.schemas.client import (
    ClientCreateSchema,
    ClientUpdateSchema,
    ClientResponseSchema
)

from app.services.client_service import (
    ClientService
)


router = APIRouter()


@router.post(
    "/",
    response_model=ClientResponseSchema
)
def create_client(
    data: ClientCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ClientService.create_client(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[ClientResponseSchema]
)
def get_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ClientService.get_clients(
        db,
        current_user
    )


@router.get(
    "/{client_id}",
    response_model=ClientResponseSchema
)
def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ClientService.get_client(
        db,
        current_user,
        client_id
    )


@router.put(
    "/{client_id}",
    response_model=ClientResponseSchema
)
def update_client(
    client_id: str,
    data: ClientUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ClientService.update_client(
        db,
        current_user,
        client_id,
        data
    )


@router.delete("/{client_id}")
def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return ClientService.delete_client(
        db,
        current_user,
        client_id
    )