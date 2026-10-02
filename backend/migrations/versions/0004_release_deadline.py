"""Immutable publication deadline for a two-stage task."""
from alembic import op
import sqlalchemy as sa

revision = '0004_release_deadline'
down_revision = '0003_checkpoints'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tasks', sa.Column('release_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_tasks_release_at', 'tasks', ['release_at'])


def downgrade():
    op.drop_index('ix_tasks_release_at', table_name='tasks')
    op.drop_column('tasks', 'release_at')
