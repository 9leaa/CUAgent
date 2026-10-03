"""Bounded daily schedules and immutable occurrence identities."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0007_schedules'
down_revision = '0006_notifications'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('schedules', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('idempotency_key', sa.String(80), nullable=False, unique=True),
        sa.Column('request_sha256', sa.String(64), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(24), nullable=False),
        sa.Column('next_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('occurrences', sa.Integer(), nullable=False),
        sa.Column('last_commit', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_schedules_next_at', 'schedules', ['next_at'])
    op.create_table('schedule_occurrences', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('schedule_id', sa.String(36), sa.ForeignKey('schedules.id'), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('prepare_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('batch_id', sa.String(36), sa.ForeignKey('batches.id'), nullable=True),
        sa.Column('source', postgresql.JSONB(), nullable=True),
        sa.Column('source_sha256', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('schedule_id', 'due_at'))
    op.create_index('ix_schedule_occurrences_schedule_id', 'schedule_occurrences', ['schedule_id'])


def downgrade():
    op.drop_index('ix_schedule_occurrences_schedule_id', table_name='schedule_occurrences')
    op.drop_table('schedule_occurrences')
    op.drop_index('ix_schedules_next_at', table_name='schedules')
    op.drop_table('schedules')
