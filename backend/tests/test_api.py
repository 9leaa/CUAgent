from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.api import create_app
from backend.models import Task
from backend.models import Artifact
from pathlib import Path
import hashlib


def test_aggregate_opt_in_preserves_legacy_and_rejects_scheduled_combination(service, payload):
    original, _ = service.submit(payload, 'pre-p5-original')
    with TestClient(create_app(service.settings)) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        old = client.post('/tasks', json=payload, headers={'Idempotency-Key': 'pre-p5-original'})
        assert old.status_code == 200 and old.json()['id'] == original
        body = {**payload, 'inputMode': 'aggregate'}
        response = client.post('/tasks', json=body, headers={'Idempotency-Key': 'aggregate-new'})
        assert response.status_code == 201
        with service.sessions() as db:
            assert db.get(Task, response.json()['id']).payload['inputMode'] == 'aggregate'
            assert 'inputMode' not in db.get(Task, original).payload
        assert client.post('/tasks', json=body, headers={'Idempotency-Key': 'aggregate-new'}).status_code == 200
        assert client.post('/tasks', json=body, headers={'Idempotency-Key': 'pre-p5-original'}).status_code == 409
        for invalid in ({**body, 'releaseAt': '2026-10-10T12:00:00+08:00'}, {**body, 'inputMode': 'anything'}):
            assert client.post('/tasks', json=invalid, headers={'Idempotency-Key': 'invalid-mode'}).status_code == 422


def test_auth_input_contract_idempotency_and_cursor(service, payload):
    app = create_app(service.settings)
    with TestClient(app) as client:
        assert client.get('/tasks').status_code == 401
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        response = client.post('/tasks', json=payload, headers={'Idempotency-Key': 'api-one'})
        assert response.status_code == 201, response.text
        task_id = response.json()['id']
        assert client.post('/tasks', json=payload, headers={'Idempotency-Key': 'api-one'}).json() == {'id': task_id, 'created': False}
        assert client.get('/tasks/' + task_id).json()['status'] == 'QUEUED'
        events = client.get('/tasks/' + task_id + '/events').json()
        assert len(events['items']) == 1
        assert client.get('/tasks/' + task_id + '/events', params={'after': events['next_cursor']}).json()['items'] == []
        assert client.get('/tasks/' + task_id + '/artifacts/report.md').status_code == 404
        assert client.post('/tasks/' + task_id + '/stop').json()['status'] == 'STOPPED'
        assert client.post('/tasks/' + task_id + '/resume').json()['status'] == 'QUEUED'
        bad = {**payload, 'notes': [{'name': '../secret.md', 'content': 'bad'}]}
        assert client.post('/tasks', json=bad, headers={'Idempotency-Key': 'escape'}).status_code == 422
        assert client.post('/tasks', content=b'x' * 262145, headers={'Idempotency-Key': 'large'}).status_code == 413


def test_new_api_instance_reads_persisted_task(service, payload):
    headers = {'Authorization': 'Bearer ' + service.settings.api_token, 'Idempotency-Key': 'restart'}
    with TestClient(create_app(service.settings)) as before:
        task_id = before.post('/tasks', json=payload, headers=headers).json()['id']
    with TestClient(create_app(service.settings)) as after:
        assert after.get('/tasks/' + task_id, headers=headers).json()['status'] == 'QUEUED'
        assert after.post('/tasks', json=payload, headers=headers).json()['created'] is False


def test_publication_requires_timezone_and_preserves_legacy_idempotency(service, payload):
    task_id, _ = service.submit(payload, 'legacy')
    with TestClient(create_app(service.settings)) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        assert client.post('/tasks', json=payload, headers={'Idempotency-Key': 'legacy'}).json()['id'] == task_id
        invalid = client.post('/tasks', json={**payload, 'releaseAt': '2026-10-03T12:00:00'}, headers={'Idempotency-Key': 'naive'})
        assert invalid.status_code == 422
        created = client.post('/tasks', json={**payload, 'releaseAt': '2026-10-03T12:00:00+08:00'}, headers={'Idempotency-Key': 'timed'})
        assert created.status_code == 201
        status = client.get('/tasks/' + created.json()['id']).json()
        assert status['release_at'].startswith('2026-10-03T04:00:00')


def test_artifact_gate_rejects_changed_bytes_and_escape(service, payload):
    # Storage unit fixture, not a claimed real model success.
    task_id, _ = service.submit(payload, 'artifact-storage')
    run = service.settings.root / 'unit-run'
    (run / 'workspace').mkdir(parents=True)
    path = run / 'workspace/report.md'
    path.write_bytes(b'original\n')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with service.sessions.begin() as db:
        task = db.get(Task, task_id)
        task.status, task.run_dir = 'SUCCEEDED', str(run)
        db.add(Artifact(task_id=task_id, name='report.md', sha256=digest, bytes=9))
    with TestClient(create_app(service.settings)) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        url = '/tasks/' + task_id + '/artifacts/report.md'
        assert client.get(url).content == b'original\n'
        path.write_bytes(b'changed!\n')
        assert client.get(url).status_code == 409
        assert client.get('/tasks/' + task_id + '/artifacts/secret.txt').status_code == 404


def test_malformed_csv_and_nul_are_input_errors(service, payload):
    with TestClient(create_app(service.settings)) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        for content in ['units\n"unclosed', 'units\n2\x00']:
            invalid = {**payload, 'csv': [{'name': 'metrics.csv', 'content': content, 'numericColumns': ['units']}]}
            assert client.post('/tasks', json=invalid, headers={'Idempotency-Key': 'invalid'}).status_code == 422
