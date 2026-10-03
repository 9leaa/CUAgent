"""Transactional local inbox, not external delivery or historical backfill."""
from alembic import op
import sqlalchemy as sa

revision = '0006_notifications'
down_revision = '0005_batches'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('notifications', sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
                    sa.Column('event_id', sa.BigInteger(), sa.ForeignKey('events.id'), nullable=False, unique=True),
                    sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id'), nullable=False),
                    sa.Column('status', sa.String(24), nullable=False),
                    sa.Column('error_code', sa.String(80), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_notifications_task_id', 'notifications', ['task_id'])


def downgrade():
    op.drop_index('ix_notifications_task_id', table_name='notifications')
    op.drop_table('notifications')
