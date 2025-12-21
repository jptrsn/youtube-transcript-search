"""add_websub_subscriptions_table

Revision ID: ef7c363526f9
Revises: c15af48eb42b
Create Date: 2025-12-18 20:11:38.019286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef7c363526f9'
down_revision: Union[str, None] = 'c15af48eb42b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create websub_subscriptions table
    op.create_table(
        'websub_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('topic_url', sa.String(length=512), nullable=False),
        sa.Column('callback_url', sa.String(length=512), nullable=False),
        sa.Column('verify_token', sa.String(length=255), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=False),
        sa.Column('subscribed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('lease_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('last_notification_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_websub_subscriptions_channel_id', 'websub_subscriptions', ['channel_id'], unique=True)
    op.create_index('ix_websub_subscriptions_expires_at', 'websub_subscriptions', ['expires_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_websub_subscriptions_expires_at', table_name='websub_subscriptions')
    op.drop_index('ix_websub_subscriptions_channel_id', table_name='websub_subscriptions')

    # Drop table
    op.drop_table('websub_subscriptions')