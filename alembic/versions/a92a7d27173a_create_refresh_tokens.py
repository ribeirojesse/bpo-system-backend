from alembic import op

import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


revision = "create_refresh_tokens"

down_revision = "0aa3531f4ee5"

branch_labels = None

depends_on = None


def upgrade():

    op.create_table(

        "refresh_tokens",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False
        ),

        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False
        ),

        sa.Column(
            "token",
            sa.String(),
            nullable=False
        ),

        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False
        ),

        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint("token"),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE"
        )

    )


def downgrade():

    op.drop_table("refresh_tokens")