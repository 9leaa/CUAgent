"""Idempotent references to original tool audit entries."""
from alembic import op
import sqlalchemy as sa

revision = '0002_audit_events'
down_revision = '0001_tasks'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('events', sa.Column('external_id', sa.String(160), nullable=True))
    op.create_unique_constraint('uq_events_task_external', 'events', ['task_id', 'external_id'])


def downgrade():
    op.drop_constraint('uq_events_task_external', 'events', type_='unique')
    op.drop_column('events', 'external_id')
