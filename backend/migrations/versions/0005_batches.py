"""Atomic, idempotent groups of independent bounded tasks."""
from alembic import op
import sqlalchemy as sa

revision = '0005_batches'
down_revision = '0004_release_deadline'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('batches', sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('idempotency_key', sa.String(80), nullable=False, unique=True),
                    sa.Column('request_sha256', sa.String(64), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('batch_items', sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
                    sa.Column('batch_id', sa.String(36), sa.ForeignKey('batches.id'), nullable=False),
                    sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id'), nullable=False),
                    sa.Column('position', sa.Integer(), nullable=False),
                    sa.UniqueConstraint('batch_id', 'position'), sa.UniqueConstraint('task_id'))
    op.create_index('ix_batch_items_batch_id', 'batch_items', ['batch_id'])


def downgrade():
    op.drop_index('ix_batch_items_batch_id', table_name='batch_items')
    op.drop_table('batch_items')
    op.drop_table('batches')
