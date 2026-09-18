from sqlalchemy.orm import Session

from app.models.closing_schedule import (
    ClosingSchedule
)


class ClosingScheduleRepository:

    @staticmethod
    def create(db: Session, data: dict):

        schedule = ClosingSchedule(**data)

        db.add(schedule)

        db.commit()

        db.refresh(schedule)

        return schedule

    @staticmethod
    def get_all(
        db: Session,
        tenant_id,
        skip: int = 0,
        limit: int = 500
    ):

        return (
            db.query(ClosingSchedule)
            .filter(
                ClosingSchedule.tenant_id == tenant_id
            )
            .order_by(
                ClosingSchedule.data_vencimento.asc()
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        schedule_id
    ):

        return db.query(
            ClosingSchedule
        ).filter(
            ClosingSchedule.id == schedule_id,
            ClosingSchedule.tenant_id == tenant_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        schedule,
        data: dict
    ):

        for key, value in data.items():
            setattr(schedule, key, value)

        db.commit()

        db.refresh(schedule)

        return schedule

    @staticmethod
    def delete(
        db: Session,
        schedule
    ):

        db.delete(schedule)

        db.commit()
