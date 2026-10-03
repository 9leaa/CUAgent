from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from pydantic import ValidationError
from backend.api import create_app
from backend.models import Attempt, Task
from backend.service import Conflict

BODY = {'kind': 'desktop-textedit', 'lines': ['交接内容', 'Next: verify']}


def owner():
    return str(uuid.uuid4())


def test_default_api_closed_and_no_task_created(service):
    with TestClient(create_app(service.settings)) as client:
        assert client.post('/desktop-tasks', json=BODY, headers={'Idempotency-Key': 'one'}).status_code == 401
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        response = client.post('/desktop-tasks', json=BODY, headers={'Idempotency-Key': 'one'})
        assert response.status_code == 503
        assert response.json()['detail'] == 'DESKTOP_TASK_EXECUTION_NOT_ENABLED'
    with service.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Task)) == 0


def test_isolated_enabled_api_idempotency_stop_and_legacy_separation(service, payload):
    with TestClient(create_app(replace(service.settings, desktop_tasks_enabled=True))) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        headers = {'Idempotency-Key': 'desktop-one'}
        response = client.post('/desktop-tasks', json=BODY, headers=headers)
        assert response.status_code == 201
        identity = response.json()['id']
        assert client.post('/desktop-tasks', json=BODY, headers=headers).json() == {'id': identity, 'created': False}
        assert client.post('/desktop-tasks', json={**BODY, 'lines': ['changed']}, headers=headers).status_code == 409
        assert client.post('/desktop-tasks', json={**BODY, 'path': '/tmp/bypass'}, headers=headers).status_code == 422
        assert client.post('/desktop-tasks', json=BODY, headers={'Idempotency-Key': '../bad'}).status_code == 422
        assert client.post('/tasks', json=BODY, headers=headers).status_code == 422
        assert client.post('/desktop-tasks', json=payload, headers=headers).status_code == 422
        state = client.get('/tasks/' + identity).json()
        assert state['kind'] == 'desktop-textedit' and state['session_id'] is None
        assert state['budget']['used'] == 0
        assert client.get('/tasks/' + identity + '/artifacts/report.md').status_code == 404
        assert client.post('/tasks/' + identity + '/stop').json()['status'] == 'STOPPED'
        assert service.claim(owner(), kind='desktop-textedit') is None
        assert client.post('/tasks/' + identity + '/resume').json()['status'] == 'QUEUED'
    with service.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0


def test_report_claim_skips_older_desktop_and_both_share_resource(service, payload):
    desktop, _ = service.submit(BODY, 'desktop')
    report, _ = service.submit(payload, 'report')
    claimed = service.claim(owner())
    assert claimed.id == report
    assert service.claim(owner(), kind='desktop-textedit') is None
    service.finish(report, claimed.owner, claimed.epoch, 'STOPPED')
    claimed = service.claim(owner(), kind='desktop-textedit')
    assert claimed.id == desktop
    assert service.claim(owner()) is None
    service.finish(desktop, claimed.owner, claimed.epoch, 'STOPPED')
    with pytest.raises(Conflict, match='DESKTOP_RECOVERY'):
        service.resume(desktop)


def test_different_kind_workers_cannot_claim_desktop_concurrently(service, payload):
    service.submit(BODY, 'desktop')
    service.submit(payload, 'report')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda kind: service.claim(owner(), kind=kind),
                                ['daily-report', 'desktop-textedit']))
    assert sum(item is not None for item in results) == 1


def test_concurrent_desktop_submission_creates_one_task(service):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: service.submit(BODY, 'same'), range(8)))
    assert len({item[0] for item in results}) == 1
    assert sum(item[1] for item in results) == 1


@pytest.mark.parametrize('kind', [None, 'unknown', 'daily-report'])
def test_unknown_or_explicit_legacy_kind_rejected_and_unclaimable(service, payload, kind):
    with pytest.raises(ValidationError):
        service.submit({**BODY, 'kind': kind}, 'invalid')
    identity, _ = service.submit(payload, 'legacy-row')
    with service.sessions.begin() as db:
        db.get(Task, identity).payload = {**payload, 'kind': kind}
    assert service.claim(owner()) is None
    assert service.claim(owner(), kind='desktop-textedit') is None
    with pytest.raises(ValueError, match='UNSUPPORTED_TASK_KIND'):
        service.claim(owner(), kind='shell')


def test_legacy_hash_body_and_idempotency_unchanged(service, payload):
    identity, created = service.submit(payload, 'legacy')
    assert created and service.submit(payload, 'legacy') == (identity, False)
    expected = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                        separators=(',', ':')).encode()).hexdigest()
    with service.sessions() as db:
        task = db.get(Task, identity)
        assert task.payload == payload and task.request_sha256 == expected
    assert service.view(identity)['kind'] == 'daily-report'
    with pytest.raises(Conflict):
        service.submit(BODY, 'legacy')
