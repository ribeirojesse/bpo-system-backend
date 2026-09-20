from datetime import date

from fastapi import HTTPException

from app.repositories.client_repository import (
    ClientRepository
)

from app.repositories.closing_schedule_repository import (
    ClosingScheduleRepository
)


class ClosingScheduleService:

    @staticmethod
    def create_schedule(
        db,
        current_user,
        data
    ):

        if data.client_id:

            client = ClientRepository.get_by_id(
                db,
                current_user.tenant_id,
                data.client_id
            )

            if not client:
                raise HTTPException(
                    status_code=404,
                    detail="Cliente não encontrado"
                )

        payload = data.model_dump()

        payload["tenant_id"] = current_user.tenant_id

        return ClosingScheduleRepository.create(
            db,
            payload
        )

    @staticmethod
    def get_schedules(
        db,
        current_user,
        skip: int = 0,
        limit: int = 500
    ):

        return ClosingScheduleRepository.get_all(
            db,
            current_user.tenant_id,
            skip,
            limit
        )

    @staticmethod
    def get_schedule(
        db,
        current_user,
        schedule_id
    ):

        schedule = ClosingScheduleRepository.get_by_id(
            db,
            current_user.tenant_id,
            schedule_id
        )

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Item de cronograma não encontrado"
            )

        return schedule

    @staticmethod
    def update_schedule(
        db,
        current_user,
        schedule_id,
        data
    ):

        schedule = ClosingScheduleService.get_schedule(
            db,
            current_user,
            schedule_id
        )

        if data.client_id:

            client = ClientRepository.get_by_id(
                db,
                current_user.tenant_id,
                data.client_id
            )

            if not client:
                raise HTTPException(
                    status_code=404,
                    detail="Cliente não encontrado"
                )

        payload = data.model_dump(
            exclude_unset=True
        )

        # Preenche/limpa data_conclusao automaticamente quando o front só
        # manda o novo status, sem obrigar a mandar a data junto.
        if payload.get("status") == "CONCLUIDO" and \
                "data_conclusao" not in payload:
            payload["data_conclusao"] = date.today()

        if payload.get("status") == "PENDENTE" and \
                "data_conclusao" not in payload:
            payload["data_conclusao"] = None

        return ClosingScheduleRepository.update(
            db,
            schedule,
            payload
        )

    @staticmethod
    def delete_schedule(
        db,
        current_user,
        schedule_id
    ):

        schedule = ClosingScheduleService.get_schedule(
            db,
            current_user,
            schedule_id
        )

        ClosingScheduleRepository.delete(
            db,
            schedule
        )

        return {
            "message": "Item de cronograma removido"
        }
