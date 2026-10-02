"""P2 initial PostgreSQL schema; frozen independently of future ORM changes."""
from alembic import op

revision = '0001_tasks'
down_revision = None
branch_labels = None
depends_on = None

DDL = """
CREATE TABLE tasks (
 id VARCHAR(36) PRIMARY KEY, idempotency_key VARCHAR(80) NOT NULL UNIQUE,
 request_sha256 VARCHAR(64) NOT NULL, payload JSONB NOT NULL,
 status VARCHAR(24) NOT NULL, error_code VARCHAR(80), session_id VARCHAR(160),
 run_dir TEXT, owner VARCHAR(36), epoch INTEGER NOT NULL DEFAULT 0,
 calls INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_tasks_status ON tasks(status);
CREATE TABLE attempts (
 id BIGSERIAL PRIMARY KEY, task_id VARCHAR(36) NOT NULL REFERENCES tasks(id),
 owner VARCHAR(36) NOT NULL, epoch INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL, finished_at TIMESTAMPTZ
);
CREATE INDEX ix_attempts_task_id ON attempts(task_id);
CREATE TABLE events (
 id BIGSERIAL PRIMARY KEY, task_id VARCHAR(36) NOT NULL REFERENCES tasks(id),
 kind VARCHAR(60) NOT NULL, data JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_events_task_id ON events(task_id);
CREATE TABLE artifacts (
 id BIGSERIAL PRIMARY KEY, task_id VARCHAR(36) NOT NULL REFERENCES tasks(id),
 name VARCHAR(40) NOT NULL, sha256 VARCHAR(64) NOT NULL, bytes INTEGER NOT NULL,
 UNIQUE(task_id,name)
);
CREATE INDEX ix_artifacts_task_id ON artifacts(task_id);
CREATE TABLE usage (task_id VARCHAR(36) PRIMARY KEY REFERENCES tasks(id), data JSONB NOT NULL);
CREATE TABLE resources (
 name VARCHAR(80) PRIMARY KEY, owner VARCHAR(36), task_id VARCHAR(36) REFERENCES tasks(id),
 epoch INTEGER NOT NULL DEFAULT 0, expires_at TIMESTAMPTZ
);
INSERT INTO resources(name,epoch) VALUES ('desktop',0)
"""


def upgrade():
    for statement in DDL.split(';'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    # Destructive migration is an explicit operator action, never startup behavior.
    for table in ['resources', 'usage', 'artifacts', 'events', 'attempts', 'tasks']:
        op.drop_table(table)
