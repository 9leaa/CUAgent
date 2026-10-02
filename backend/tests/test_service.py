from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import uuid
import pytest
from sqlalchemy import func, select
from backend.control import write_control
from backend.models import Event, Resource, Task, utcnow
from backend.service import Conflict


def test_concurrent_idempotent_submission(service, payload):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: service.submit(payload, 'same-key'), range(12)))
    assert len({r[0] for r in results}) == 1
    assert sum(r[1] for r in results) == 1
    with service.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Task)) == 1
        assert db.scalar(select(func.count()).select_from(Event)) == 1
    with pytest.raises(Conflict, match='IDEMPOTENCY_BODY_CONFLICT'):
        service.submit({**payload, 'date': '2026-10-03'}, 'same-key')


def test_two_workers_cannot_claim_one_resource(service, payload):
    service.submit(payload, 'one')
    service.submit(payload, 'two')
    owners = [str(uuid.uuid4()), str(uuid.uuid4())]
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(service.claim, owners))
    assert sum(task is not None for task in claims) == 1
    task = next(t for t in claims if t)
    assert service.heartbeat(task.id, task.owner, task.epoch) is False
    with pytest.raises(Conflict, match='STALE'):
        service.heartbeat(task.id, str(uuid.uuid4()), task.epoch)


def test_stop_is_durable_and_heartbeat_cannot_undo_it(service, payload):
    task_id, _ = service.submit(payload, 'one')
    task = service.claim(str(uuid.uuid4()))
    assert service.stop(task_id) == 'STOP_REQUESTED'
    assert service.heartbeat(task_id, task.owner, task.epoch) is True
    control = json.loads((service.settings.root / 'controls' / (task_id + '.json')).read_text())
    assert control['stopped'] is True
    with pytest.raises(Conflict, match='OWNER_STILL_ACTIVE'):
        service.resume(task_id)
    service.finish(task_id, task.owner, task.epoch, 'STOPPED')
    assert service.resume(task_id) == 'QUEUED'
    resumed = service.claim(str(uuid.uuid4()))
    assert resumed.id == task_id and resumed.epoch > task.epoch
    assert json.loads((service.settings.root / 'controls' / (task_id + '.json')).read_text())['stopped'] is False


def test_expired_owner_cannot_finish_or_overwrite_new_control(service, payload):
    task_id, _ = service.submit(payload, 'one')
    task = service.claim(str(uuid.uuid4()))
    with service.sessions.begin() as db:
        db.get(Resource, 'desktop').expires_at = utcnow() - timedelta(seconds=1)
    with pytest.raises(Conflict, match='STALE'):
        service.finish(task_id, task.owner, task.epoch, 'SUCCEEDED', result={})
    assert service.claim(str(uuid.uuid4())) is None
    assert service.view(task_id)['status'] == 'BLOCKED'
    service.resume(task_id)
    newer = service.claim(str(uuid.uuid4()))
    path = service.settings.root / 'controls' / (task_id + '.json')
    before = path.read_bytes()
    with pytest.raises(ValueError, match='stale'):
        write_control(path, run_id='p2-' + task_id, epoch=task.epoch, owner=task.owner, expires_at=0)
    assert path.read_bytes() == before and newer.epoch > task.epoch


def test_queued_stop_no_attempt_or_budget_reset(service, payload):
    task_id, _ = service.submit(payload, 'one')
    assert service.stop(task_id) == 'STOPPED'
    assert service.claim(str(uuid.uuid4())) is None
    assert service.view(task_id)['budget'] == {'used': 0, 'limit': 30}
    assert service.resume(task_id) == 'QUEUED'
    task = service.claim(str(uuid.uuid4()))
    service.progress(task.id, task.owner, task.epoch, 10)
    with pytest.raises(Conflict, match='INVALID_BUDGET'):
        service.progress(task.id, task.owner, task.epoch, 0)
    with pytest.raises(Conflict, match='INDEPENDENT_VERIFICATION'):
        service.finish(task.id, task.owner, task.epoch, 'SUCCEEDED')


def test_audit_import_is_idempotent_private_and_identity_bound(service, payload):
    task_id, _ = service.submit(payload, 'audit')
    task = service.claim(str(uuid.uuid4()))
    service.record_prepared(task_id, task.owner, task.epoch, '/unused/run', 'original-session')
    row = {'runId': 'p2-' + task_id, 'sessionId': 'original-session',
           'event': 'dispatch', 'callId': 'one', 'name': 'workspace_read',
           'used': 1, 'args': {'content': 'private source'}, 'prompt': 'private prompt'}
    service.import_audit(task_id, task.owner, task.epoch, [row])
    service.import_audit(task_id, task.owner, task.epoch, [row])
    with service.sessions() as db:
        events = list(db.scalars(select(Event).where(Event.external_id.is_not(None))))
        assert len(events) == 1
        assert events[0].data == {'callId': 'one', 'name': 'workspace_read', 'used': 1}
    with pytest.raises(Conflict, match='AUDIT_IDENTITY_CHANGED'):
        service.import_audit(task_id, task.owner, task.epoch, [{**row, 'sessionId': 'different'}])
    with pytest.raises(Conflict, match='STALE'):
        service.import_audit(task_id, str(uuid.uuid4()), task.epoch, [row])


def test_checkpoint_survives_service_recreation_and_rejects_stale_owner(service, payload):
    from backend.service import TaskService
    task_id, _ = service.submit(payload, 'checkpoint')
    task = service.claim(str(uuid.uuid4()))
    service.record_prepared(task_id, task.owner, task.epoch, '/unused/run', 'same-session')
    evidence = {'runId': 'p2-' + task_id, 'sessionId': 'same-session',
                'used': 7, 'auditBytes': 100, 'auditSha256': 'a' * 64,
                'pending': {'unknown-call': 'workspace_write'}, 'artifacts': {}}
    service.checkpoint(task_id, task.owner, task.epoch, 'observing', evidence)
    fresh = TaskService(service.sessions, service.settings)
    assert fresh.view(task_id)['checkpoint']['phase'] == 'observing'
    assert fresh.view(task_id)['budget']['used'] == 7
    with fresh.sessions() as db:
        assert db.get(Task, task_id).checkpoint['evidence'] == evidence
    with pytest.raises(Conflict, match='REGRESSED'):
        fresh.checkpoint(task_id, task.owner, task.epoch, 'observing', {**evidence, 'used': 6})
    with pytest.raises(Conflict, match='REGRESSED'):
        fresh.checkpoint(task_id, task.owner, task.epoch, 'observing', {**evidence, 'auditBytes': 99})
    with pytest.raises(Conflict, match='IDENTITY_CHANGED'):
        fresh.checkpoint(task_id, task.owner, task.epoch, 'observing', {**evidence, 'sessionId': 'other'})
    with fresh.sessions.begin() as db:
        db.get(Resource, 'desktop').expires_at = utcnow() - timedelta(seconds=1)
    with pytest.raises(Conflict, match='STALE'):
        fresh.checkpoint(task_id, task.owner, task.epoch, 'verifying', evidence)
