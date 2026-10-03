"""Controlled-clock DB tests, never evidence of elapsed real days or model execution."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event as Signal
from unittest.mock import Mock
from sqlalchemy import func, select
import pytest
from backend.batches import digest
from backend.models import Batch, Occurrence, Task
from backend.schemas import ScheduleSubmission
from backend.schedules import DAY, GRACE, PREPARE_LEASE, ScheduleService
from backend.service import Conflict

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
BASE = 'a' * 40
END = 'b' * 40


def config(runs=7):
    return dict(startAt=NOW.isoformat(), timezone='UTC', runs=runs,
                branch='p5-personal-workflows', baselineCommit=BASE)


@pytest.fixture
def scheduler(service, payload):
    clock = [NOW]
    def collect(ticket):
        return [{'workflow': 'project-changes', 'source': {'fromExclusive': ticket['lastCommit'], 'toInclusive': END},
                 'payload': payload},
                {'workflow': 'task-operations', 'source': {'fromInclusive': (ticket['dueAt'] - DAY).isoformat(),
                  'toExclusive': ticket['dueAt'].isoformat()}, 'payload': payload}]
    value = ScheduleService(service, collect=Mock(side_effect=collect), permitted=Mock(return_value=True), clock=lambda: clock[0])
    return value, clock


def count_tasks(scheduler):
    with scheduler.sessions() as db:
        return db.scalar(select(func.count()).select_from(Task))


def test_due_once_atomic_snapshot_batch_and_exhaustion(scheduler):
    svc, clock = scheduler
    identity, _ = svc.create(config(1), 'one')
    clock[0] -= timedelta(seconds=1)
    assert svc.tick(identity)['status'] == 'NOT_DUE'
    clock[0] = NOW
    result = svc.tick(identity)
    assert result['status'] == 'SUBMITTED' and count_tasks(svc) == 2
    assert svc.tick(identity)['status'] == 'EXHAUSTED'
    with svc.sessions() as db:
        row = db.get(Occurrence, result['id'])
        assert row.source_sha256 == digest(row.source)
        assert db.get(Batch, result['batch_id']) is not None
    assert svc.create(config(1), 'one') == (identity, False)
    assert svc.collect.call_count == 1


def test_no_permit_waits_then_misses_without_dispatch(scheduler):
    svc, clock = scheduler
    svc.permitted.return_value = False
    identity, _ = svc.create(config(1), 'permission')
    assert svc.tick(identity)['status'] == 'WAITING_PERMISSION'
    assert svc.view(identity)['occurrences'] == 0
    clock[0] += GRACE + timedelta(seconds=1)
    assert svc.tick(identity)['status'] == 'MISSED'
    assert count_tasks(svc) == 0 and svc.collect.call_count == 0


def test_seven_missed_days_are_recorded_never_caught_up_as_tasks(scheduler):
    svc, clock = scheduler
    identity, _ = svc.create(config(), 'missed')
    clock[0] += 8 * DAY
    for _ in range(7): assert svc.tick(identity)['status'] == 'MISSED'
    assert svc.tick(identity)['status'] == 'EXHAUSTED'
    assert len(svc.view(identity)['items']) == 7 and count_tasks(svc) == 0
    svc.collect.assert_not_called()


def test_pause_while_collecting_is_not_blocked_by_db_lock(scheduler):
    svc, _ = scheduler
    identity, _ = svc.create(config(), 'pause')
    original = svc.collect.side_effect
    def collect(ticket):
        svc.pause(identity)
        return original(ticket)
    svc.collect.side_effect = collect
    assert svc.tick(identity)['status'] == 'CANCELLED'
    assert svc.tick(identity)['status'] == 'PAUSED' and count_tasks(svc) == 0


def test_parallel_schedulers_and_restart_do_not_duplicate(scheduler):
    svc, _ = scheduler
    identity, _ = svc.create(config(), 'parallel')
    entered, release = Signal(), Signal()
    original = svc.collect.side_effect
    def collect(ticket):
        entered.set()
        assert release.wait(5)
        return original(ticket)
    svc.collect.side_effect = collect
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(svc.tick, identity)
        assert entered.wait(5)
        assert svc.tick(identity)['status'] == 'PREPARING'
        release.set()
        assert first.result()['status'] == 'SUBMITTED'
    restarted = ScheduleService(svc.batches.tasks, collect=svc.collect, permitted=svc.permitted, clock=svc.clock)
    assert restarted.tick(identity)['status'] == 'NOT_DUE'
    assert count_tasks(svc) == 2 and svc.collect.call_count == 1


def test_preparation_crash_expires_without_recollecting(scheduler):
    svc, clock = scheduler
    identity, _ = svc.create(config(1), 'crash')
    ticket = svc.prepare(identity)
    clock[0] += PREPARE_LEASE
    assert svc.tick(identity)['status'] == 'EXHAUSTED'
    assert svc.view(identity)['items'][0]['status'] == 'PREPARATION_EXPIRED'
    assert svc.finish_preparation(ticket, source_error=True)['status'] == 'PREPARATION_EXPIRED'
    assert count_tasks(svc) == 0
    svc.collect.assert_not_called()


@pytest.mark.parametrize('fault', ['source', 'permission', 'changed-window', 'changed-commit', 'malformed'])
def test_source_error_or_revocation_creates_no_tasks(scheduler, fault):
    svc, _ = scheduler
    identity, _ = svc.create(config(1), 'fault')
    original = svc.collect.side_effect
    def collect(ticket):
        if fault == 'source': raise OSError('private data must not be exposed')
        if fault == 'malformed': return [{}, {}]
        data = original(ticket)
        if fault == 'permission': svc.permitted.return_value = False
        if fault == 'changed-window': data[1]['source']['toExclusive'] = (NOW + DAY).isoformat()
        if fault == 'changed-commit': data[0]['source']['fromExclusive'] = END
        return data
    svc.collect.side_effect = collect
    assert svc.tick(identity)['status'] == ('PERMISSION_REVOKED' if fault == 'permission' else 'SOURCE_ERROR')
    assert count_tasks(svc) == 0


def test_batch_insertion_failure_rolls_back_snapshot_and_all_children(scheduler, monkeypatch):
    svc, clock = scheduler
    identity, _ = svc.create(config(1), 'rollback')
    original = svc.batches.tasks.event
    def interrupted(db, task, kind, **data):
        if data['position'] == 1: raise RuntimeError('database interruption')
        original(db, task, kind, **data)
    monkeypatch.setattr(svc.batches.tasks, 'event', interrupted)
    with pytest.raises(RuntimeError): svc.tick(identity)
    assert count_tasks(svc) == 0
    with svc.sessions() as db:
        row = db.scalar(select(Occurrence))
        assert row.status == 'PREPARING' and row.source is None and row.batch_id is None
        assert db.scalar(select(func.count()).select_from(Batch)) == 0
    clock[0] += PREPARE_LEASE
    svc.tick(identity)
    assert svc.view(identity)['items'][0]['status'] == 'PREPARATION_EXPIRED'


def test_config_limits_timezone_and_idempotency(scheduler):
    svc, clock = scheduler
    identity, _ = svc.create(config(1), 'configuration')
    clock[0] += DAY
    assert svc.create(config(1), 'configuration') == (identity, False)
    with pytest.raises(Conflict): svc.create(config(2), 'configuration')
    for changes in ({'runs': 8}, {'runs': True}, {'startAt': '2026-10-03T00:00:00'}, {'timezone': 'No/Such_Zone'},
                    {'timezone': 'Asia/Shanghai'}, {'branch': '--all'}, {'baselineCommit': 'HEAD'}):
        with pytest.raises(ValueError): ScheduleSubmission.model_validate({**config(), **changes})
    with pytest.raises(ValueError): svc.create(config(), 'past-new-plan')
