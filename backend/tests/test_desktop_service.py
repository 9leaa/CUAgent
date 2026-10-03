from contextlib import contextmanager
import json
import socket
import subprocess
import sys
import time

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend import desktop_service as entry
from backend.desktop_collect import save_exclusive


def available_port():
    for port in range(18100, 19000):
        with socket.socket() as listener:
            try:
                listener.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('No isolated test port available')


@pytest.fixture
def profile(service, tmp_path):
    baseline = tmp_path / 'baseline.env'
    original = {'CUAGENT_DATABASE_URL': service.settings.database_url,
                'CUAGENT_BACKEND_ROOT': str(service.settings.root),
                'CUAGENT_BACKEND_TOKEN': service.settings.api_token,
                'CUAGENT_BASE_TASKS': str(service.settings.base_tasks),
                'CUAGENT_DSH_COOKIE_FILE': str(service.settings.cookie_file)}
    save_exclusive(baseline, ''.join(k + '=' + v + '\n' for k, v in original.items()).encode())
    root = tmp_path / 'isolated'
    try:
        yield entry.initialize(baseline_env=baseline, root=root, port=available_port())
    finally:
        intent = root / 'initialization-intent.json'
        if intent.exists():
            name = json.loads(intent.read_text())['database']
            assert name.startswith('cuagent_p6_service_')
            admin = create_engine(make_url(service.settings.database_url).set(database='postgres'),
                                  isolation_level='AUTOCOMMIT')
            try:
                with admin.connect() as connection:
                    connection.execute(text('DROP DATABASE IF EXISTS "' + name + '" WITH (FORCE)'))
            finally:
                admin.dispose()


def test_initialization_is_distinct_and_never_overwrites(profile, service):
    loaded = entry.load_profile(profile)
    assert loaded.settings.database_url != service.settings.database_url
    assert loaded.settings.api_token != service.settings.api_token
    assert loaded.settings.root == profile.parent / 'jobs'
    assert loaded.settings.desktop_tasks_enabled
    assert profile.stat().st_mode & 0o777 == 0o600
    assert loaded.settings.root.stat().st_mode & 0o777 == 0o700
    before = profile.read_bytes()
    with pytest.raises(FileExistsError):
        entry.initialize(baseline_env=loaded.baseline_env, root=profile.parent, port=loaded.port)
    assert profile.read_bytes() == before
    # The baseline database remains reachable and has not received desktop work.
    from sqlalchemy import select, func
    from backend.models import Task
    with service.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Task)) == 0


def test_isolated_api_rejects_other_task_types_and_wrong_auth(profile):
    config = entry.load_profile(profile)
    with TestClient(entry.create_desktop_app(config)) as client:
        body = {'kind': 'desktop-textedit', 'lines': ['test']}
        assert client.post('/desktop-tasks', json=body, headers={'Idempotency-Key': 'test'}).status_code == 401
        headers = {'Authorization': 'Bearer ' + config.settings.api_token, 'Idempotency-Key': 'test'}
        for path in ['/tasks', '/batches', '/schedules', '/tasks/' + 'a' * 36 + '/resume']:
            assert client.post(path, headers=headers, json={}).status_code == 409
        submitted = client.post('/desktop-tasks', headers=headers, json=body)
        assert submitted.status_code == 201


@pytest.mark.parametrize('mutation', ['same_database', 'same_token', 'port', 'version', 'unknown'])
def test_profile_refuses_unsafe_edits(profile, service, mutation):
    body = json.loads(profile.read_text())
    if mutation == 'same_database':
        body['databaseUrl'] = service.settings.database_url
    elif mutation == 'same_token':
        body['apiToken'] = service.settings.api_token
    elif mutation == 'port':
        body['port'] = 18089
    elif mutation == 'version':
        body['version'] = True
    else:
        body['enableModel'] = True
    profile.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        entry.load_profile(profile)


def test_init_refuses_overlap_without_writing(profile, service):
    loaded = entry.load_profile(profile)
    target = service.settings.root / 'must-not-exist'
    with pytest.raises(ValueError):
        entry.initialize(baseline_env=loaded.baseline_env, root=target, port=loaded.port)
    assert not target.exists()


def test_profile_refuses_symlinks_public_mode_and_duplicates(profile):
    link = profile.parent / 'link.json'; link.symlink_to(profile)
    with pytest.raises(ValueError):
        entry.load_profile(link)
    profile.chmod(0o644)
    with pytest.raises(ValueError):
        entry.load_profile(profile)
    profile.chmod(0o600)
    profile.write_text('{"version":1,"version":1}')
    with pytest.raises(ValueError):
        entry.load_profile(profile)


def test_occupied_port_does_not_start_or_stop_another_service(profile):
    loaded = entry.load_profile(profile)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', loaded.port)); listener.listen()
        with pytest.raises(OSError):
            entry.serve(loaded)
        assert listener.getsockname()[1] == loaded.port


@contextmanager
def running_api(profile):
    loaded = entry.load_profile(profile)
    process = subprocess.Popen([sys.executable, '-m', 'backend.desktop_service', 'serve', '--profile', str(profile)],
                               cwd=entry.PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url='http://127.0.0.1:' + str(loaded.port), trust_env=False, timeout=.3,
                          headers={'Authorization': 'Bearer ' + loaded.settings.api_token}) as client:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                assert process.poll() is None, 'isolated API exited before readiness'
                try:
                    if client.get('/health').status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.05)
            else:
                pytest.fail('isolated API did not become ready')
            yield client
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)


def test_real_http_cli_and_restart_preserve_original_task(profile, tmp_path):
    spec = tmp_path / 'input.json'
    spec.write_text('{"kind":"desktop-textedit","lines":["真实HTTP队列测试"]}')
    command = [sys.executable, '-m', 'backend.client', 'desktop-submit', '--desktop-service', str(profile),
               '--spec', str(spec), '--key', 'original-request']
    def submit():
        result = subprocess.run(command, cwd=entry.PROJECT, capture_output=True, timeout=10)
        assert result.returncode == 0, 'submission client failed'
        return json.loads(result.stdout)
    with running_api(profile) as client:
        first = submit()
        assert first['created']
        state = client.get('/tasks/' + first['id']).json()
        assert state['status'] == 'QUEUED' and state['session_id'] is None and state['budget']['used'] == 0
        assert client.get('/tasks/' + first['id'] + '/artifacts/result.txt').status_code != 200
    with running_api(profile) as client:
        repeated = submit()
        assert not repeated['created'] and repeated['id'] == first['id']
        response = client.post('/tasks/' + first['id'] + '/stop')
        assert response.status_code == 200 and response.json()['status'] == 'STOPPED'
        state = client.get('/tasks/' + first['id']).json()
        assert state['budget']['used'] == 0 and state['session_id'] is None and not state['artifacts']


def test_cli_redacts_config_errors(tmp_path, capsys, monkeypatch):
    path = tmp_path / 'invalid.json'
    save_exclusive(path, b'{"databaseUrl":"credential-must-not-leak"}')
    monkeypatch.setattr(sys, 'argv', ['desktop-service', 'serve', '--profile', str(path)])
    with pytest.raises(SystemExit) as error:
        entry.main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert 'credential-must-not-leak' not in output.out + output.err
    assert json.loads(output.out)['result'] == 'REFUSED'
