"""create push_devices and notifications tables

Suporte ao app mobile: aparelhos registrados pra push (Expo) e histórico
de notificações por usuário.

Revision ID: e7a1c3d9f2b4
Revises: c4e8a1f2b3d7
Create Date: 2026-09-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e7a1c3d9f2b4'
down_revision: Union[str, Sequence[str], None] = 'c4e8a1f2b3d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'push_devices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=True),
        sa.Column('device_name', sa.String(), nullable=True),
        sa.Column(
            'ativo',
            sa.Boolean(),
            server_default=sa.text('true'),
            nullable=False
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_push_devices_token')
    )

    op.create_index(
        'ix_push_devices_user_id', 'push_devices', ['user_id']
    )

    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('tipo', sa.String(), nullable=False),
        sa.Column('titulo', sa.String(), nullable=False),
        sa.Column('mensagem', sa.String(), nullable=False),
        sa.Column(
            'data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        ),
        sa.Column('lida_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        'ix_notifications_user_id', 'notifications', ['user_id']
    )


def downgrade() -> None:
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')

    op.drop_index('ix_push_devices_user_id', table_name='push_devices')
    op.drop_table('push_devices')
