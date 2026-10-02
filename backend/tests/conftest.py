import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from backend.config import Settings
from backend.db import database
from backend.service import TaskService


@pytest.fixture
def service(tmp_path):
    base = make_url(os.environ['CUAGENT_DATABASE_URL'])
    name = 'cuagent_test_' + uuid.uuid4().hex
    admin = create_engine(base.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as connection:
        connection.execute(text('CREATE DATABASE "' + name + '"'))
    url = base.set(database=name).render_as_string(hide_password=False)
    env = {**os.environ, 'CUAGENT_DATABASE_URL': url}
    subprocess.run([sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'], env=env, check=True, capture_output=True)
    root = tmp_path / 'private'
    root.mkdir(mode=0o700)
    settings = Settings(url, 'test-private-token-' + 'x' * 32, root,
                        Path('/unused/tasks.json'), Path('/unused/cookie.json'))
    engine, sessions = database(url)
    svc = TaskService(sessions, settings)
    yield svc
    engine.dispose()
    with admin.connect() as connection:
        connection.execute(text('DROP DATABASE "' + name + '" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture
def payload():
    return {'date': '2026-10-02', 'notes': [{'name': 'progress.md', 'content': '# A\n## 进展\n完成接口\n## 阻塞\n无\n## 下一步\n测试\n'}],
            'csv': [{'name': 'metrics.csv', 'content': 'units\n2\n4\n', 'numericColumns': ['units']}]}
