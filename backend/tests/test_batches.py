from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from fastapi.testclient import TestClient
from sqlalchemy import func, select
import pytest
from backend.api import create_app
from backend.batches import BatchService
from backend.models import Batch, BatchItem, Event, Task
from backend.service import Conflict


def body(payload):
    return {'tasks': [payload, {**payload, 'date': '2026-10-03', 'inputMode': 'aggregate'}]}


def counts(service):
    with service.sessions() as db:
        return tuple(db.scalar(select(func.count()).select_from(model)) for model in (Batch, BatchItem, Task, Event))


def test_atomic_create_repeat_and_order(service, payload):
    batches = BatchService(service)
    identity, created = batches.submit(body(payload), 'batch-one')
    assert created and counts(service) == (1, 2, 2, 2)
    assert batches.submit(body(payload), 'batch-one') == (identity, False)
    view = batches.view(identity)
    assert view['status'] == 'QUEUED' and len(view['items']) == 2
    with service.sessions() as db:
        assert [db.get(Task, item['id']).payload['date'] for item in view['items']] == ['2026-10-02', '2026-10-03']
        assert all(db.get(Task, item['id']).calls == 0 for item in view['items'])


def test_invalid_or_conflicting_batch_leaves_no_partial_tasks(service, payload):
    batches = BatchService(service)
    with pytest.raises(ValueError): batches.submit({'tasks': [payload]}, 'too-small')
    with pytest.raises(ValueError): batches.submit({'tasks': [payload]*4}, 'too-large')
    invalid = body(payload); invalid['tasks'][1]['inputMode'] = 'unapproved'
    with pytest.raises(ValueError): batches.submit(invalid, 'bad-child')
    assert counts(service) == (0, 0, 0, 0)
    batches.submit(body(payload), 'fixed')
    changed = body(payload); changed['tasks'].reverse()
    with pytest.raises(Conflict): batches.submit(changed, 'fixed')
    assert counts(service) == (1, 2, 2, 2)


def test_second_child_failure_rolls_back_batch_tasks_and_events(service, payload, monkeypatch):
    original = service.event
    def fail_second(db, task, kind, **data):
        if data['position'] == 1: raise RuntimeError('injected transaction failure')
        original(db, task, kind, **data)
    monkeypatch.setattr(service, 'event', fail_second)
    with pytest.raises(RuntimeError): BatchService(service).submit(body(payload), 'rollback')
    assert counts(service) == (0, 0, 0, 0)
    monkeypatch.setattr(service, 'event', original)
    assert BatchService(service).submit(body(payload), 'rollback')[1]


def test_concurrent_or_lost_ack_submission_returns_one_original_batch(service, payload):
    barrier = Barrier(4)
    def submit(_):
        barrier.wait()
        return BatchService(service).submit(body(payload), 'concurrent')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(submit, range(4)))
    assert len({r[0] for r in results}) == 1
    assert sum(r[1] for r in results) == 1
    assert counts(service) == (1, 2, 2, 2)
    assert BatchService(service).submit(body(payload), 'concurrent') == (results[0][0], False)


def test_partial_failure_is_not_batch_success_and_stop_preserves_completed(service, payload):
    batches = BatchService(service)
    identity, _ = batches.submit(body(payload), 'mixed')
    ids = batches.task_ids(identity)
    with service.sessions.begin() as db:
        db.get(Task, ids[0]).status = 'SUCCEEDED'
        db.get(Task, ids[1]).status = 'FAILED'
    assert batches.view(identity)['status'] == 'COMPLETED_WITH_ERRORS'
    assert [i['status'] for i in batches.stop(identity)['items']] == ['SUCCEEDED', 'FAILED']


def test_partial_stop_can_finish_without_recreating_tasks(service, payload, monkeypatch):
    batches = BatchService(service)
    identity, _ = batches.submit(body(payload), 'stop')
    ids = batches.task_ids(identity)
    original = service.stop
    def interrupted(task_id):
        if task_id == ids[1]: raise RuntimeError('operator disconnected')
        return original(task_id)
    monkeypatch.setattr(service, 'stop', interrupted)
    with pytest.raises(RuntimeError): batches.stop(identity)
    assert [i['status'] for i in batches.view(identity)['items']] == ['STOPPED', 'QUEUED']
    monkeypatch.setattr(service, 'stop', original)
    assert batches.stop(identity)['status'] == 'STOPPED'
    assert batches.task_ids(identity) == ids
    assert counts(service)[:3] == (1, 2, 2)


def test_batch_api_auth_validation_persistence_and_stop(service, payload):
    with TestClient(create_app(service.settings)) as client:
        assert client.post('/batches', json=body(payload)).status_code == 401
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        response = client.post('/batches', json=body(payload), headers={'Idempotency-Key': 'api-batch'})
        assert response.status_code == 201, response.text
        identity = response.json()['id']
        assert client.post('/batches', json=body(payload), headers={'Idempotency-Key': 'api-batch'}).status_code == 200
        assert client.get('/batches/' + identity).json()['status'] == 'QUEUED'
        assert client.post('/batches/' + identity + '/stop').json()['status'] == 'STOPPED'
        assert client.post('/batches', json={'tasks': [payload]}, headers={'Idempotency-Key': 'small'}).status_code == 422
        assert client.post('/batches', json=body(payload), headers={'Idempotency-Key': '../bad'}).status_code == 422
    with TestClient(create_app(service.settings)) as reopened:
        assert reopened.get('/batches/' + identity, headers={'Authorization': 'Bearer ' + service.settings.api_token}).json()['status'] == 'STOPPED'
