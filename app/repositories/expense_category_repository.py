from sqlalchemy.orm import Session

from app.models.expense_category import (
    ExpenseCategory
)


class ExpenseCategoryRepository:

    @staticmethod
    def create(
        db: Session,
        data: dict
    ):

        category = ExpenseCategory(
            **data
        )

        db.add(category)

        db.commit()

        db.refresh(category)

        return category

    @staticmethod
    def get_all(
        db: Session,
        tenant_id
    ):

        return (
            db.query(
                ExpenseCategory
            )
            .filter(
                ExpenseCategory.tenant_id
                == tenant_id
            )
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        category_id
    ):

        return (
            db.query(
                ExpenseCategory
            )
            .filter(
                ExpenseCategory.id
                == category_id,

                ExpenseCategory.tenant_id
                == tenant_id
            )
            .first()
        )

    @staticmethod
    def update(
        db: Session,
        category,
        data: dict
    ):

        for key, value in data.items():

            setattr(
                category,
                key,
                value
            )

        db.commit()

        db.refresh(category)

        return category

    @staticmethod
    def delete(
        db: Session,
        category
    ):

        db.delete(category)

        db.commit()