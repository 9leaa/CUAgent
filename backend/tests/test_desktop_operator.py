from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import uuid

import pytest

from backend import desktop_operator as operator
from backend.desktop_collect import save_exclusive
from backend.desktop_worker import DesktopWorker
from backend.models import Resource, Task
from backend.tests.test_desktop_service import profile
from backend.tests.test_desktop_worker import Adapter


@pytest.fixture
def quota(tmp_path):
    now = datetime.now(timezone.utc)
    profile = tmp_path / 'profile.json'; save_exclusive(profile, b'{"synthetic":true}')
    task_id = str(uuid.uuid4())
    record = {'version': 1, 'taskId': task_id,
              'profileSha256': hashlib.sha256(profile.read_bytes()).hexdigest(),
              'source': 'Codex get_usage_limits', 'checkedAt': now.isoformat(),
              'expiresAt': (now + timedelta(minutes=5)).isoformat(),
              'remainingPercent': 3, 'ordinaryUsageAllowed': True,
              'creditsBalance': operator.CREDITS, 'resetCardsUsed': 0}
    path = tmp_path / 'quota.json'
    def build(**changes):
        path.write_text(json.dumps({**record, **changes})); path.chmod(0o600)
        return operator.QuotaGate(tmp_path, profile, task_id, path, clock=lambda: now)
    return build, path, profile, now


def test_exact_quota_threshold_and_five_minute_deadline(quota):
    build, _, _, now = quota
    gate = build()
    assert gate.check()
    gate.clock = lambda: now + timedelta(minutes=5)
    with pytest.raises(ValueError): gate.check()
    assert not gate.stop.exists()


@pytest.mark.parametrize('remaining', [3, 3.01, 17, 39.99, 40, 100])
def test_updated_desktop_threshold_allows_three_percent_and_above(quota, remaining):
    build, _, _, _ = quota
    gate = build(remainingPercent=remaining)
    assert gate.check()
    assert not gate.stop.exists()


@pytest.mark.parametrize('changes', [
    {'remainingPercent': 2.99}, {'ordinaryUsageAllowed': False},
    {'creditsBalance': '0'}, {'resetCardsUsed': 1},
])
def test_real_policy_stop_is_persistent_across_new_good_record(quota, changes):
    build, _, _, _ = quota
    gate = build(**changes)
    with pytest.raises(RuntimeError, match='POLICY_STOP'): gate.check()
    assert gate.stop.stat().st_mode & 0o777 == 0o600
    fresh = build()
    with pytest.raises(RuntimeError, match='STOP_LATCHED'): fresh.check()


@pytest.mark.parametrize('changes', [
    {'taskId': str(uuid.uuid4())}, {'profileSha256': 'a' * 64}, {'source': 'copied'},
    {'remainingPercent': True}, {'remainingPercent': float('nan')},
    {'resetCardsUsed': False}, {'version': True}, {'extraPermission': True},
    {'checkedAt': '2099-01-01T00:00:00+00:00'}, {'expiresAt': '2099-01-01T00:00:00+00:00'},
    {'checkedAt': '2026-01-01T00:00:00'},
])
def test_invalid_quota_never_grants_or_fabricates_policy_stop(quota, changes):
    build, _, _, _ = quota
    gate = build(**changes)
    with pytest.raises(ValueError): gate.check()
    assert not gate.stop.exists()


@pytest.mark.parametrize('target', ['quota', 'profile'])
def test_changed_record_cannot_extend_original_permission(quota, target):
    build, path, profile, _ = quota
    gate = build()
    target_path = path if target == 'quota' else profile
    target_path.write_text(target_path.read_text() + ' ')
    with pytest.raises(ValueError, match='CHANGED'): gate.check()


def test_targeted_claim_does_not_pick_another_task(service):
    first, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['first']}, 'first')
    second, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['second']}, 'second')
    assert service.claim('owner', kind='desktop-textedit', task_id=str(uuid.uuid4())) is None
    selected = service.claim('owner', kind='desktop-textedit', task_id=second)
    assert selected.id == second
    assert service.view(first)['status'] == 'QUEUED'


def test_refused_admission_has_no_claim_or_adapter_side_effect(service):
    task_id, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['test']}, 'only')
    adapter = Mock()
    worker = DesktopWorker(service, adapter, shared_lock=service.settings.root / 'lock')
    def reject():
        raise ValueError('quota or live preflight refused')
    with pytest.raises(ValueError): worker.run_once(task_id=task_id, before_claim=reject)
    assert service.view(task_id)['status'] == 'QUEUED'
    adapter.prepare.assert_not_called()
    with pytest.raises(RuntimeError, match='ADMISSION_REFUSED'):
        worker.run_once(task_id=task_id, before_claim=lambda: False)


def test_admission_runs_inside_shared_lock_and_selects_exact_task(service):
    first, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['first']}, 'first')
    second, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['second']}, 'second')
    worker = DesktopWorker(service, Mock(), shared_lock=service.settings.root / 'lock')
    def admission():
        with worker.shared_lock.open('rb') as other:
            with pytest.raises(BlockingIOError): fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert service.view(second)['status'] == 'QUEUED'
        return True
    worker.execute = Mock(return_value={'synthetic': True})
    assert worker.run_once(task_id=second, before_claim=admission) == {'synthetic': True}
    assert worker.execute.call_args.args[0].id == second
    assert service.view(first)['status'] == 'QUEUED'


@pytest.fixture
def live_gate(service, tmp_path, monkeypatch):
    base = tmp_path / 'baseline.env'
    save_exclusive(base, ('CUAGENT_DATABASE_URL=' + service.settings.database_url + '\n'
        'CUAGENT_BACKEND_ROOT=' + str(service.settings.root) + '\nCUAGENT_BACKEND_TOKEN=synthetic\n'
        'CUAGENT_BASE_TASKS=/unused/tasks\nCUAGENT_DSH_COOKIE_FILE=/unused/cookie\n').encode())
    profile = SimpleNamespace(baseline_env=base)
    quota = Mock(); quota.task_id = str(uuid.uuid4())
    run = Mock(side_effect=[b'/usr/bin/safe-process\n',
                           b'{"username":"mvpagent","model":"VirtualMac2,1","unlocked":true}'])
    monkeypatch.setattr(operator, 'run_bounded', run)
    gate = operator.LiveGate(profile, quota, Path('/synthetic/ssh'))
    return gate, run


def test_live_gate_checks_real_idle_pg_and_mock_vm(live_gate):
    gate, run = live_gate
    assert gate()
    assert gate.quota.check.call_count == 2
    assert run.call_args_list[0].args[0] == ['/bin/ps', '-axo', 'command=']
    assert run.call_args_list[1].args[0][:3] == ['/synthetic/ssh', '-F', '/dev/null']


def test_live_gate_refuses_p5_queued_work_without_ssh(service, live_gate):
    service.submit({'kind': 'desktop-textedit', 'lines': ['busy']}, 'busy')
    gate, run = live_gate
    with pytest.raises(RuntimeError, match='NOT_IDLE'): gate()
    run.assert_not_called()


def test_live_gate_refuses_unresolved_owner(service, live_gate):
    with service.sessions.begin() as db:
        db.get(Resource, 'desktop').owner = 'uncertain-owner'
    gate, run = live_gate
    with pytest.raises(RuntimeError, match='NOT_IDLE'): gate()
    run.assert_not_called()


def test_live_gate_refuses_old_worker_and_locked_vm(live_gate):
    gate, run = live_gate
    run.side_effect = [b'/private/python -m backend.worker\n']
    with pytest.raises(RuntimeError, match='MUST_BE_STOPPED'): gate()
    assert run.call_count == 1
    run.side_effect = [b'', b'{"username":"mvpagent","model":"VirtualMac2,1","unlocked":false}']
    with pytest.raises(RuntimeError, match='VM_NOT_READY'): gate()


def test_live_gate_refuses_other_task_or_changed_baseline(live_gate):
    gate, run = live_gate
    with pytest.raises(ValueError, match='OTHER_TASK'): gate(SimpleNamespace(id=str(uuid.uuid4())))
    gate.profile.baseline_env.write_text(gate.profile.baseline_env.read_text() + '\n')
    with pytest.raises(ValueError, match='CONFIGURATION_CHANGED'): gate()
    run.assert_not_called()


def test_live_gate_refuses_due_schedule(service, live_gate):
    from backend.models import Schedule
    with service.sessions.begin() as db:
        db.add(Schedule(id=str(uuid.uuid4()), idempotency_key='due', request_sha256='a' * 64,
            config={}, status='ACTIVE', last_commit='b' * 40,
            next_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
    gate, run = live_gate
    with pytest.raises(RuntimeError, match='SCHEDULE_TOO_CLOSE'): gate()
    run.assert_not_called()


def test_live_gate_respects_existing_baseline_quota_stop(service, live_gate):
    (service.settings.root / 'scheduler-operator-stop.json').write_text('{}')
    gate, run = live_gate
    with pytest.raises(RuntimeError, match='STOP_LATCHED'): gate()
    run.assert_not_called()


@pytest.fixture
def operator_files(profile):
    root = profile.parent
    for name in ['home', 'build']:
        (root / name).mkdir(mode=0o700)
    (root / 'build').chmod(0o755)  # Public build dependencies are not credentials.
    for name in ['node', 'known-hosts', 'askpass']:
        save_exclusive(root / name, b'synthetic-not-executed')
    (root / 'node').chmod(0o700); (root / 'askpass').chmod(0o700)
    execution = root / 'execution.json'
    save_exclusive(execution, json.dumps({'version': 1, 'node': str(root / 'node'),
        'officialHome': str(root / 'home'), 'buildTools': str(root / 'build'),
        'knownHosts': str(root / 'known-hosts'), 'askpass': str(root / 'askpass'),
        'guestCommit': 'a' * 40, 'guestManifestSha256': 'b' * 64, 'tunnelPort': 19099}).encode())
    loaded = operator.load_profile(profile)
    engine, sessions = operator.database(loaded.settings.database_url)
    service = operator.TaskService(sessions, loaded.settings)
    first, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['first']}, 'first')
    task_id, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['second']}, 'second')
    now = datetime.now(timezone.utc)
    quota = root / 'synthetic-quota.json'
    save_exclusive(quota, json.dumps({'version': 1, 'taskId': task_id,
        'profileSha256': hashlib.sha256(profile.read_bytes()).hexdigest(), 'source': 'Codex get_usage_limits',
        'checkedAt': now.isoformat(), 'expiresAt': (now + timedelta(minutes=5)).isoformat(),
        'remainingPercent': 40, 'ordinaryUsageAllowed': True,
        'creditsBalance': operator.CREDITS, 'resetCardsUsed': 0}).encode())
    yield dict(profile_path=profile, execution_path=execution, quota_path=quota,
               task_id=task_id, cutover_approved=True), service, first
    engine.dispose()


def test_operator_composes_original_worker_with_synthetic_external_edges(operator_files, monkeypatch):
    args, service, first = operator_files
    gate = Mock(return_value=True)
    gate_factory = Mock(return_value=gate)
    monkeypatch.setattr(operator, 'LiveGate', gate_factory)
    adapter_calls = []
    def adapter(svc, settings, *, execution_gate):
        assert settings.cutover_authorized and settings.tunnel_port == 19099
        assert execution_gate is gate
        instance = Adapter(svc)
        adapter_calls.append(instance)
        return instance
    monkeypatch.setattr(operator, 'DesktopTaskAdapter', adapter)
    result = operator.worker_once(**args)
    assert result['result'] == 'EXECUTION_RECORDED'
    assert result['outcome']['status'] == 'SUCCEEDED' and result['outcome']['restoreConfirmed']
    assert service.view(first)['status'] == 'QUEUED'
    assert service.view(args['task_id'])['status'] == 'SUCCEEDED'
    assert gate.call_count == 1  # Real adapter separately rechecks at prepare/start/prompt.
    assert adapter_calls[0].calls == ['prepare', 'start', 'poll', 'verify', 'restore']
    assert (args['profile_path'].parent / ('desktop-launch-' + args['task_id'] + '.json')).is_file()
    with pytest.raises(ValueError, match='UNATTEMPTED'):
        operator.worker_once(**args)
    assert service.view(first)['status'] == 'QUEUED'


def test_operator_refuses_without_approval_and_before_live_actions(operator_files, monkeypatch):
    args, service, _ = operator_files
    adapter = Mock()
    monkeypatch.setattr(operator, 'DesktopTaskAdapter', adapter)
    with pytest.raises(ValueError, match='EXPLICIT_CUTOVER'):
        operator.worker_once(**{**args, 'cutover_approved': False})
    assert service.view(args['task_id'])['status'] == 'QUEUED'
    adapter.assert_not_called()


def test_operator_live_refusal_does_not_consume_task_or_create_claim_intent(operator_files, monkeypatch):
    args, service, _ = operator_files
    monkeypatch.setattr(operator, 'LiveGate', lambda *_: Mock(side_effect=RuntimeError('not ready')))
    adapter = Mock()
    monkeypatch.setattr(operator, 'DesktopTaskAdapter', lambda *a, **k: adapter)
    with pytest.raises(RuntimeError, match='not ready'):
        operator.worker_once(**args)
    assert service.view(args['task_id'])['status'] == 'QUEUED'
    adapter.prepare.assert_not_called()
    assert not (args['profile_path'].parent / ('desktop-launch-' + args['task_id'] + '.json')).exists()
    receipts = list(args['profile_path'].parent.glob('admission-*/refusal.json'))
    assert len(receipts) == 1 and json.loads(receipts[0].read_text())['errorType'] == 'RuntimeError'
