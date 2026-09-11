from sqlalchemy.orm import Session

from app.models.expense_subcategory import (
    ExpenseSubcategory
)

from app.models.expense_category import (
    ExpenseCategory
)


class ExpenseSubcategoryRepository:

    @staticmethod
    def create(
        db: Session,
        data: dict
    ):

        subcategory = ExpenseSubcategory(
                **data
            )

        db.add(subcategory)

        db.commit()

        db.refresh(subcategory)

        return subcategory

    @staticmethod
    def get_all(
        db: Session,
        tenant_id,
        skip: int = 0,
        limit: int = 100
    ):

        return (
            db.query(
                ExpenseSubcategory
            )
            .join(
                ExpenseCategory,
                ExpenseCategory.id
                ==
                ExpenseSubcategory.category_id
            )
            .filter(
                ExpenseCategory.tenant_id
                == tenant_id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        tenant_id,
        subcategory_id
    ):

        return (
            db.query(
                ExpenseSubcategory
            )
            .join(
                ExpenseCategory,
                ExpenseCategory.id
                ==
                ExpenseSubcategory.category_id
            )
            .filter(
                ExpenseSubcategory.id
                == subcategory_id,

                ExpenseCategory.tenant_id
                == tenant_id
            )
            .first()
        )

    @staticmethod
    def update(
        db: Session,
        subcategory,
        data: dict
    ):

        for key, value in data.items():

            setattr(
                subcategory,
                key,
                value
            )

        db.commit()

        db.refresh(subcategory)

        return subcategory

    @staticmethod
    def delete(
        db: Session,
        subcategory
    ):

        db.delete(subcategory)

        db.commit()