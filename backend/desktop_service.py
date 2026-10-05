"""Isolated desktop queue service. Does not launch a Worker, App or VM."""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.config import Settings
from backend.desktop_collect import private_path, save_exclusive

PROJECT = Path(__file__).resolve().parents[1]


def read_private(path):
    path = private_path(path, directory=False)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > 32768):
            raise ValueError('PRIVATE_SERVICE_CONFIG_REQUIRED')
        data = stream.read(32769)
    if len(data) > 32768:
        raise ValueError('SERVICE_CONFIG_TOO_LARGE')
    return data.decode('utf-8')


def baseline(path):
    values = {}
    for line in read_private(path).splitlines():
        if not line or line.startswith('#'):
            continue
        key, value = line.split('=', 1)
        if key in values:
            raise ValueError('DUPLICATE_BASELINE_FIELD')
        values[key] = value
    for name in ('CUAGENT_DATABASE_URL', 'CUAGENT_BACKEND_ROOT', 'CUAGENT_BACKEND_TOKEN',
                 'CUAGENT_BASE_TASKS', 'CUAGENT_DSH_COOKIE_FILE'):
        if not values.get(name):
            raise ValueError('INCOMPLETE_BASELINE')
    return values


def check_port(port):
    if type(port) is not int or not 18100 <= port <= 18999:
        raise ValueError('ISOLATED_LOOPBACK_PORT_18100_TO_18999_REQUIRED')


def check_isolation(root, url, old):
    root = private_path(root, directory=True)
    previous = Path(old['CUAGENT_BACKEND_ROOT']).resolve(strict=True)
    if root.is_relative_to(previous) or previous.is_relative_to(root):
        raise ValueError('OVERLAPPING_SERVICE_ROOTS')
    original, target = make_url(old['CUAGENT_DATABASE_URL']), make_url(url)
    if (not re.fullmatch(r'cuagent_p6_service_[0-9a-f]{32}', target.database or '')
            or target.database == original.database or target.set(database=original.database) != original
            or target.host != '127.0.0.1' or target.drivername != 'postgresql+psycopg'):
        raise ValueError('ISOLATED_LOCAL_DATABASE_REQUIRED')
    return root, target


@dataclass(frozen=True)
class ServiceProfile:
    settings: Settings
    port: int
    baseline_env: Path


def load_profile(path, *, kind='desktop-textedit'):
    if kind not in ('desktop-textedit', 'project-handoff'):
        raise ValueError('UNSUPPORTED_DESKTOP_SERVICE_KIND')
    path = Path(path).absolute()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('DUPLICATE_SERVICE_FIELD')
            result[key] = value
        return result
    data = json.loads(read_private(path), object_pairs_hook=unique)
    if (not isinstance(data, dict) or set(data) !=
            {'version', 'baselineEnv', 'databaseUrl', 'apiToken', 'port'}
            or type(data['version']) is not int or data['version'] != 1):
        raise ValueError('INVALID_SERVICE_PROFILE')
    old = baseline(data['baselineEnv'])
    check_port(data['port'])
    root, _ = check_isolation(path.parent, data['databaseUrl'], old)
    token = data['apiToken']
    if (not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token)
            or token == old['CUAGENT_BACKEND_TOKEN']):
        raise ValueError('INDEPENDENT_AUTH_REQUIRED')
    jobs = private_path(root / 'jobs', directory=True)
    settings = Settings(data['databaseUrl'], token, jobs,
                        Path(old['CUAGENT_BASE_TASKS']), Path(old['CUAGENT_DSH_COOKIE_FILE']),
                        desktop_tasks_enabled=kind == 'desktop-textedit', handoff_tasks_enabled=kind == 'project-handoff')
    return ServiceProfile(settings, data['port'], Path(data['baselineEnv']))


def initialize(*, baseline_env, root, port):
    check_port(port)
    baseline_env = private_path(baseline_env, directory=False)
    old = baseline(baseline_env)
    root = Path(root).absolute()
    # Require an existing private parent; never recursively create arbitrary paths.
    private_path(root.parent, directory=True)
    previous = Path(old['CUAGENT_BACKEND_ROOT']).resolve(strict=True)
    if (root.resolve() != root or root.is_relative_to(previous) or previous.is_relative_to(root)):
        raise ValueError('OVERLAPPING_OR_NONCANONICAL_SERVICE_ROOT')
    root.mkdir(mode=0o700)
    name = 'cuagent_p6_service_' + uuid.uuid4().hex
    target = make_url(old['CUAGENT_DATABASE_URL']).set(database=name)
    url = target.render_as_string(hide_password=False)
    check_isolation(root, url, old)
    save_exclusive(root / 'initialization-intent.json', json.dumps({'version': 1, 'database': name}).encode())
    admin = create_engine(target.set(database='postgres'), isolation_level='AUTOCOMMIT')
    try:
        with admin.connect() as connection:
            connection.execute(text('CREATE DATABASE "' + name + '"'))
    finally:
        admin.dispose()
    # Explicit URL overrides inherited values; no migration can target the baseline.
    result = subprocess.run([sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'],
                            cwd=PROJECT, env={**os.environ, 'CUAGENT_DATABASE_URL': url},
                            capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError('ISOLATED_MIGRATION_FAILED')
    (root / 'jobs').mkdir(mode=0o700)
    profile = root / 'service.json'
    save_exclusive(profile, json.dumps({'version': 1, 'baselineEnv': str(baseline_env),
        'databaseUrl': url, 'apiToken': secrets.token_urlsafe(32), 'port': port}).encode())
    load_profile(profile)
    return profile


def create_desktop_app(profile):
    from fastapi.responses import JSONResponse
    from backend.api import create_app
    app = create_app(profile.settings)

    @app.middleware('http')
    async def desktop_only(request, call_next):
        endpoint = '/handoff-tasks' if profile.settings.handoff_tasks_enabled else '/desktop-tasks'
        if request.method == 'POST' and not (request.url.path == endpoint or
                re.fullmatch(r'/tasks/[0-9a-f-]{36}/stop', request.url.path)):
            return JSONResponse({'detail': 'DESKTOP_ONLY_SERVICE'}, status_code=409)
        return await call_next(request)
    return app


def serve(profile):
    import uvicorn
    # Bind once before starting; occupied ports fail, never kill another listener.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', profile.port))
        listener.listen(128)
        uvicorn.run(create_desktop_app(profile), fd=listener.fileno(), access_log=False,
                    log_level='warning')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--baseline-env', type=Path, required=True)
    init.add_argument('--root', type=Path, required=True)
    init.add_argument('--port', type=int, required=True)
    api = sub.add_parser('serve')
    api.add_argument('--profile', type=Path, required=True)
    api.add_argument('--kind', choices=['desktop-textedit', 'project-handoff'], default='desktop-textedit')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            profile = initialize(baseline_env=args.baseline_env, root=args.root, port=args.port)
            print(json.dumps({'result': 'INITIALIZED', 'profile': str(profile), 'workerStarted': False}))
        else:
            serve(load_profile(args.profile, kind=args.kind))
    except Exception:
        # Database/library exceptions can contain connection credentials.
        print(json.dumps({'result': 'REFUSED', 'reason': 'DESKTOP_SERVICE_NOT_READY',
                          'action': 'Check private configuration or initialization intent; do not overwrite or retry blindly.'}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
