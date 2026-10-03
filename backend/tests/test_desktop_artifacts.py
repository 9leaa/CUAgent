"""Synthetic artifacts test delivery only, never claim GUI acceptance."""
import hashlib
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from backend.api import create_app
from backend.models import Artifact, Task
from backend.notifications import Inbox
from backend.service import Conflict


@pytest.fixture
def delivery(service):
    body = {'kind': 'desktop-textedit', 'lines': ['交接内容', 'next step']}
    identity, _ = service.submit(body, 'delivery')
    task = service.claim(str(uuid.uuid4()), kind='desktop-textedit')
    run = service.settings.root / identity
    workspace = run / 'workspace'; workspace.mkdir(parents=True, mode=0o700)
    service.record_prepared(identity, task.owner, task.epoch, run, 'synthetic-session')
    document = '交接内容\nnext step\n'.encode()
    artifacts = {'document.txt': document, 'result.txt': document + b'\n'}
    for name, data in artifacts.items():
        (workspace / name).write_bytes(data)
    result = {'status': 'SUCCEEDED', 'kind': 'desktop-textedit', 'sessionId': 'synthetic-session',
              'artifacts': {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}}
    return task, workspace, artifacts, result


def test_success_download_sha_and_notification_type(service, delivery):
    task, workspace, artifacts, result = delivery
    service.finish(task.id, task.owner, task.epoch, 'SUCCEEDED', result=result)
    with TestClient(create_app(service.settings)) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        for name, data in artifacts.items():
            response = client.get('/tasks/' + task.id + '/artifacts/' + name)
            assert response.status_code == 200 and response.content == data
            assert response.headers['etag'] == '"' + result['artifacts'][name] + '"'
            assert response.headers['content-type'].startswith('text/plain')
        assert client.get('/tasks/' + task.id + '/artifacts/report.md').status_code == 404
        (workspace / 'document.txt').write_bytes(b'tampered')
        assert client.get('/tasks/' + task.id + '/artifacts/document.txt').status_code == 409
    notice, = Inbox(service.sessions).listing()['items']
    assert notice['artifact_urls'] == ['/tasks/' + task.id + '/artifacts/' + name for name in artifacts]


@pytest.mark.parametrize('fault', ['missing', 'extra', 'kind', 'session', 'hash', 'content', 'symlink', 'stopped'])
def test_invalid_delivery_rolls_back_success_and_artifacts(service, delivery, fault):
    task, workspace, artifacts, result = delivery
    if fault == 'missing': result['artifacts'].pop('result.txt')
    if fault == 'extra': result['artifacts']['report.md'] = '0' * 64
    if fault == 'kind': result['kind'] = 'daily-report'
    if fault == 'session': result['sessionId'] = 'other'
    if fault == 'stopped': service.stop(task.id)
    if fault == 'hash': result['artifacts']['result.txt'] = '0' * 64
    if fault == 'content':
        (workspace / 'result.txt').write_bytes(b'wrong')
        result['artifacts']['result.txt'] = hashlib.sha256(b'wrong').hexdigest()
    if fault == 'symlink':
        (workspace / 'result.txt').unlink()
        (workspace / 'result.txt').symlink_to(workspace / 'document.txt')
    with pytest.raises(Conflict):
        service.finish(task.id, task.owner, task.epoch, 'SUCCEEDED', result=result)
    with service.sessions() as db:
        assert db.get(Task, task.id).status == ('STOP_REQUESTED' if fault == 'stopped' else 'RUNNING')
        assert db.scalar(select(func.count()).select_from(Artifact)) == 0
    assert Inbox(service.sessions).listing()['items'] == []


def test_stopped_task_has_no_download_or_success_urls(service, delivery):
    task, _, _, _ = delivery
    service.finish(task.id, task.owner, task.epoch, 'STOPPED')
    with TestClient(create_app(service.settings)) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        assert client.get('/tasks/' + task.id + '/artifacts/document.txt').status_code == 404
    assert Inbox(service.sessions).listing()['items'][0]['artifact_urls'] == []


def test_success_label_without_registered_artifacts_does_not_invent_links(service, payload):
    identity, _ = service.submit(payload, 'missing-artifacts')
    with service.sessions.begin() as db:
        task = db.get(Task, identity)
        task.status = 'SUCCEEDED'
        service.event(db, task, 'finished', status='SUCCEEDED')
    assert Inbox(service.sessions).listing()['items'][0]['artifact_urls'] == []
