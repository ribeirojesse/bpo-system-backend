from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    require_role
)

from app.models.user import User

from app.schemas.closing_schedule import (
    ClosingScheduleCreateSchema,
    ClosingScheduleUpdateSchema,
    ClosingScheduleResponseSchema
)

from app.services.closing_schedule_service import (
    ClosingScheduleService
)


router = APIRouter()


# Cronograma de fechamentos é uma ferramenta interna do ADMIN (carteira),
# não faz parte do portal do CLIENTE.


@router.post(
    "/",
    response_model=ClosingScheduleResponseSchema
)
def create_schedule(
    data: ClosingScheduleCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClosingScheduleService.create_schedule(
        db,
        current_user,
        data
    )


@router.get(
    "/",
    response_model=list[ClosingScheduleResponseSchema]
)
def get_schedules(
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClosingScheduleService.get_schedules(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/{schedule_id}",
    response_model=ClosingScheduleResponseSchema
)
def get_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClosingScheduleService.get_schedule(
        db,
        current_user,
        schedule_id
    )


@router.put(
    "/{schedule_id}",
    response_model=ClosingScheduleResponseSchema
)
def update_schedule(
    schedule_id: str,
    data: ClosingScheduleUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClosingScheduleService.update_schedule(
        db,
        current_user,
        schedule_id,
        data
    )


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    return ClosingScheduleService.delete_schedule(
        db,
        current_user,
        schedule_id
    )
