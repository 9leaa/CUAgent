"""Local operator entrypoint. Never prints credentials."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT / '.runtime/backend.env'


def load_env():
    if ENV_FILE.stat().st_mode & 0o077:
        raise ValueError('private backend.env required')
    values = {}
    for line in ENV_FILE.read_text().splitlines():
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            values[key] = value
    return {**os.environ, **values}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'db-up', 'migrate', 'api', 'worker', 'scheduler', 'test'])
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.command == 'init':
        root = PROJECT / '.runtime/backend'
        root.mkdir(mode=0o700, exist_ok=True)
        password = secrets.token_hex(24)
        values = {'CUAGENT_DB_PASSWORD': password,
                  'CUAGENT_DATABASE_URL': f'postgresql+psycopg://cuagent:{password}@127.0.0.1:55432/cuagent',
                  'CUAGENT_BACKEND_TOKEN': secrets.token_urlsafe(32), 'CUAGENT_BACKEND_ROOT': str(root),
                  'CUAGENT_BASE_TASKS': str(PROJECT / '.runtime/runs/a1_preset_20261002_001/tasks.json'),
                  'CUAGENT_DSH_COOKIE_FILE': str(PROJECT / '.runtime/runs/c2_a0_20261001_001/developer-cookie.json')}
        with ENV_FILE.open('x') as file:
            ENV_FILE.chmod(0o600)
            file.write(''.join(f'{key}={value}\n' for key, value in values.items()))
        print('Private backend environment created; no credentials printed.')
        return
    env = load_env()
    if args.command == 'db-up':
        command = ['docker', 'compose', '--project-name', 'cuagent-p2', '--env-file', str(ENV_FILE),
                   '-f', str(PROJECT / 'backend/compose.yml'), 'up', '-d', '--wait']
    elif args.command == 'migrate':
        command = [sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head']
    elif args.command == 'api':
        command = [sys.executable, '-m', 'uvicorn', 'backend.api:production_app', '--factory', '--host', '127.0.0.1', '--port', '18089', '--no-access-log']
    elif args.command == 'test':
        command = [sys.executable, '-m', 'pytest', '-q', 'backend/tests']
    elif args.command == 'scheduler':
        command = [sys.executable, '-m', 'backend.schedule_runner'] + (['--once'] if args.once else [])
    else:
        command = [sys.executable, '-m', 'backend.worker'] + (['--once'] if args.once else [])
    os.execvpe(command[0], command, env)


if __name__ == '__main__':
    main()
