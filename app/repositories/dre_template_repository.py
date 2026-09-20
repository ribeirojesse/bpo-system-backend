from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.dre_template import DreTemplate


class DreTemplateRepository:

    @staticmethod
    def create(db: Session, data: dict):

        template = DreTemplate(**data)

        db.add(template)

        db.commit()

        db.refresh(template)

        return template

    @staticmethod
    def get_all_for_admin(db: Session, tenant_id):

        return (
            db.query(DreTemplate)
            .filter(
                DreTemplate.tenant_id == tenant_id,
                DreTemplate.ativo == True,  # noqa: E712
            )
            .order_by(DreTemplate.nome)
            .all()
        )

    @staticmethod
    def get_all_for_client(db: Session, tenant_id, client_id):

        # Modelos do próprio cliente + modelos "padrão da carteira"
        # (client_id nulo), nunca modelos de outro cliente.
        return (
            db.query(DreTemplate)
            .filter(
                DreTemplate.tenant_id == tenant_id,
                DreTemplate.ativo == True,  # noqa: E712
                or_(
                    DreTemplate.client_id == client_id,
                    DreTemplate.client_id.is_(None),
                ),
            )
            .order_by(DreTemplate.nome)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, tenant_id, template_id):

        return db.query(DreTemplate).filter(
            DreTemplate.id == template_id,
            DreTemplate.tenant_id == tenant_id,
        ).first()

    @staticmethod
    def update(db: Session, template, data: dict):

        for key, value in data.items():
            setattr(template, key, value)

        db.commit()

        db.refresh(template)

        return template

    @staticmethod
    def delete(db: Session, template):

        db.delete(template)

        db.commit()
