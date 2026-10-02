"""Durable recovery evidence and execution phase."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0003_checkpoints'
down_revision = '0002_audit_events'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tasks', sa.Column('checkpoint', JSONB(), nullable=True))


def downgrade():
    op.drop_column('tasks', 'checkpoint')
