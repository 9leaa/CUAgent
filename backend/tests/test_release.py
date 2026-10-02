from datetime import timedelta
import uuid
from backend.models import Task, utcnow


def test_waiting_release_is_not_claimed_early_and_resumes_original_budget(service, payload):
    release = utcnow() + timedelta(hours=1)
    task_id, _ = service.submit({**payload, 'releaseAt': release.isoformat()}, 'scheduled')
    task = service.claim(str(uuid.uuid4()))
    service.record_prepared(task_id, task.owner, task.epoch, '/unused/run', 'original-session')
    evidence = {'runId': 'p2-' + task_id, 'sessionId': 'original-session', 'used': 6,
                'auditBytes': 100, 'auditSha256': 'a' * 64, 'pending': {}, 'artifacts': {}}
    service.checkpoint(task_id, task.owner, task.epoch, 'observing', evidence)
    service.wait_for_release(task_id, task.owner, task.epoch)
    assert service.view(task_id)['status'] == 'WAITING_RELEASE'
    assert service.claim(str(uuid.uuid4())) is None
    assert service.stop(task_id) == 'STOPPED'
    assert service.resume(task_id) == 'WAITING_RELEASE'
    assert service.claim(str(uuid.uuid4())) is None
    # Unit-only clock fixture: no production deadline is modified.
    with service.sessions.begin() as db:
        db.get(Task, task_id).release_at = utcnow() - timedelta(seconds=1)
    resumed = service.claim(str(uuid.uuid4()))
    assert resumed.id == task_id and resumed.session_id == 'original-session'
    assert resumed.calls == 6 and resumed.epoch > task.epoch


def test_waiting_task_releases_resource_for_other_work(service, payload):
    task_id, _ = service.submit({**payload, 'releaseAt': (utcnow() + timedelta(hours=1)).isoformat()}, 'waiting')
    task = service.claim(str(uuid.uuid4()))
    service.record_prepared(task_id, task.owner, task.epoch, '/unused/run', 'original-session')
    service.checkpoint(task_id, task.owner, task.epoch, 'observing', {
        'runId': 'p2-' + task_id, 'sessionId': 'original-session', 'used': 5,
        'auditBytes': 1, 'auditSha256': 'a' * 64, 'pending': {}, 'artifacts': {}})
    service.wait_for_release(task_id, task.owner, task.epoch)
    other_id, _ = service.submit(payload, 'other')
    assert service.claim(str(uuid.uuid4())).id == other_id
