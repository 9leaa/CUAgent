"""Synthetic adapter validates orchestration, not real GUI or model behavior."""
import hashlib
import json
import time
from unittest.mock import Mock
import pytest
from backend.desktop_contract import DesktopSubmission
from backend.desktop_worker import DesktopWorker, PreparedDesktop


class Adapter:
    def __init__(self, service, fault=None):
        self.service, self.fault, self.calls = service, fault, []

    def prepare(self, task):
        self.calls.append('prepare')
        self.task = task
        if self.fault == 'prepare': raise RuntimeError('prepare failed')
        root = self.service.settings.root / ('p2-' + task.id)
        (root / 'workspace').mkdir(parents=True, mode=0o700)
        self.client = Mock()
        self.client.identity = dict(version=1, runId='p2-' + task.id, owner=task.owner, epoch=task.epoch)
        self.client.clock = time.monotonic
        self.client.renew.side_effect = lambda seq, authority: {'deadline': authority()}
        self.client.revoke.return_value = {'stopped': True}
        if self.fault == 'revoke': self.client.revoke.side_effect = RuntimeError('unknown')
        return PreparedDesktop(root, 'synthetic-session', self.client)

    def start(self, prepared):
        self.calls.append('start')
        if self.fault == 'start': raise RuntimeError('prompt acknowledgement lost')
        if self.fault == 'stopped': self.service.stop(self.task.id)

    def poll(self, prepared):
        self.calls.append('poll')
        return {'terminal': True, 'rawCalls': 31 if self.fault == 'budget' else 5,
                'pendingCalls': 1 if self.fault == 'pending' else 0}

    def cancel(self, prepared): self.calls.append('cancel')

    def verify(self, prepared):
        self.calls.append('verify')
        assert self.client.revoke.called
        if self.fault == 'verify': raise ValueError('synthetic evidence incomplete')
        document = DesktopSubmission.model_validate(self.task.payload).expected_document()
        artifacts = {'document.txt': document, 'result.txt': document + b'\n'}
        for name, data in artifacts.items(): (prepared.run / 'workspace' / name).write_bytes(data)
        return {'status': 'SUCCEEDED', 'kind': 'desktop-textedit', 'sessionId': prepared.session_id,
                'artifacts': {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}}

    def restore(self, prepared):
        self.calls.append('restore')
        if self.fault == 'restore': raise RuntimeError('restore failed')


def worker(service, fault=None):
    service.submit({'kind': 'desktop-textedit', 'lines': ['synthetic']}, 'desktop')
    adapter = Adapter(service, fault)
    return DesktopWorker(service, adapter, shared_lock=service.settings.root / 'desktop-worker.lock'), adapter


def test_synthetic_lifecycle_delivers_after_stop_and_verify(service):
    instance, adapter = worker(service)
    result = instance.run_once()
    assert result['status'] == 'SUCCEEDED' and result['restoreConfirmed'] and not result['quarantined']
    assert adapter.calls == ['prepare', 'start', 'poll', 'verify', 'restore']
    assert service.view(result['taskId'])['status'] == 'SUCCEEDED'
    assert instance.run_once() is None


def test_failure_diagnostics_preserve_phase_without_sensitive_exception(service):
    instance, adapter = worker(service)
    adapter.poll = Mock(side_effect=ValueError('Authorization: Bearer SECRET_SENTINEL'))
    result = instance.run_once()
    assert result['executionFailure'] == dict(phase='poll-session-and-guest', category='VALIDATION_ERROR',
        started=True, terminalObserved=False, authorityLost=False)
    assert result['quarantined'] and not result['restoreConfirmed']
    assert 'SECRET_SENTINEL' not in json.dumps(result)
    for path in service.settings.root.glob('desktop-outcome-*.json'):
        assert 'SECRET_SENTINEL' not in path.read_text()
        assert path.stat().st_mode & 0o077 == 0
    assert service.view(result['taskId'])['status'] == 'RUNNING'
    with pytest.raises(RuntimeError, match='QUARANTINED'): instance.run_once()


def test_heartbeat_during_prepare_and_verify_never_regrants_revoked_guest(service, monkeypatch):
    import json
    import threading
    instance, adapter = worker(service)
    prepare_pulse, verify_pulse = threading.Event(), threading.Event()
    original_heartbeat = service.heartbeat
    original_prepare, original_verify = adapter.prepare, adapter.verify
    def heartbeat(*args, **kwargs):
        result = original_heartbeat(*args, **kwargs)
        if kwargs.get('dispatch_stopped'):
            assert json.loads((service.settings.root / 'controls' / (args[0] + '.json')).read_text())['stopped'] is True
            verify_pulse.set()
        elif not hasattr(adapter, 'client'):
            prepare_pulse.set()
        return result
    monkeypatch.setattr(service, 'heartbeat', heartbeat)
    def prepare(task):
        assert prepare_pulse.wait(5), 'DB heartbeat missing during preparation'
        return original_prepare(task)
    def verify(prepared):
        renewals = adapter.client.renew.call_count
        assert verify_pulse.wait(5), 'DB heartbeat missing during verification'
        assert adapter.client.renew.call_count == renewals
        return original_verify(prepared)
    adapter.prepare, adapter.verify = prepare, verify
    result = instance.run_once()
    assert result['status'] == 'SUCCEEDED'


@pytest.mark.parametrize('fault', ['prepare', 'start', 'revoke', 'pending', 'budget', 'stopped'])
def test_unconfirmed_execution_is_quarantined_and_never_replayed(service, fault):
    instance, adapter = worker(service, fault)
    result = instance.run_once()
    assert result['quarantined'] and result['status'] == 'BLOCKED'
    assert 'verify' not in adapter.calls
    assert adapter.calls.count('start') <= 1
    assert service.view(result['taskId'])['status'] != 'SUCCEEDED'
    replacement = DesktopWorker(service, Adapter(service), shared_lock=instance.shared_lock)
    with pytest.raises(RuntimeError, match='QUARANTINED'): replacement.run_once()


def test_stop_during_preparation_never_starts_session(service):
    instance, adapter = worker(service)
    original = adapter.prepare
    def prepare(task):
        prepared = original(task)
        service.stop(task.id)
        return prepared
    adapter.prepare = prepare
    result = instance.run_once()
    assert result['status'] == 'BLOCKED' and result['quarantined']
    assert adapter.calls == ['prepare']
    assert not adapter.client.renew.called


def test_verification_failure_does_not_deliver_artifacts(service):
    instance, adapter = worker(service, 'verify')
    result = instance.run_once()
    assert result['status'] == 'UNVERIFIED' and result['restoreConfirmed']
    assert service.view(result['taskId'])['artifacts'] == []


def test_requested_stop_settles_only_after_terminal_stopped_idle_proof(service):
    instance, adapter = worker(service, 'stopped')
    original = adapter.poll
    adapter.poll = lambda prepared: {**original(prepared), 'guestStopped': True}
    adapter.usage = lambda prepared: {'available': True, 'totalTokens': 7}
    result = instance.run_once()
    assert result['status'] == 'STOPPED' and result['restoreConfirmed'] and not result['quarantined']
    assert 'verify' not in adapter.calls and adapter.calls.count('start') == 1
    state = service.view(result['taskId'])
    assert state['status'] == 'STOPPED' and not state['artifacts'] and state['usage']['totalTokens'] == 7


@pytest.mark.parametrize('fault', ['not-stopped', 'pending', 'not-terminal', 'owner-lost', 'bad-raw'])
def test_stop_ack_without_required_proof_keeps_quarantine(service, fault):
    instance, adapter = worker(service, 'stopped')
    original = adapter.poll
    count = 0
    def poll(prepared):
        nonlocal count
        count += 1
        if count > 2: raise RuntimeError('observation unavailable')
        value = {**original(prepared), 'guestStopped': True}
        if count == 2:
            if fault == 'not-stopped': value['guestStopped'] = False
            if fault == 'pending': value['pendingCalls'] = 1
            if fault == 'not-terminal': value['terminal'] = False
            if fault == 'bad-raw': value['rawCalls'] = True
            if fault == 'owner-lost':
                from sqlalchemy import update
                from backend.models import Resource, utcnow
                from datetime import timedelta
                with service.sessions.begin() as db:
                    db.execute(update(Resource).values(expires_at=utcnow() - timedelta(seconds=1)))
        return value
    adapter.poll = poll
    result = instance.run_once()
    assert result['quarantined'] and result['status'] == 'BLOCKED'
    assert 'restore' not in adapter.calls and 'verify' not in adapter.calls
    assert service.view(result['taskId'])['status'] == 'STOP_REQUESTED'


def test_restore_failure_is_separate_from_business_success_and_blocks_reuse(service):
    instance, adapter = worker(service, 'restore')
    result = instance.run_once()
    assert result['status'] == 'SUCCEEDED' and result['quarantined']
    assert not result['restoreConfirmed'] and result['restoreError']
    with pytest.raises(RuntimeError, match='QUARANTINED'): instance.run_once()


def test_shared_lock_prevents_claiming(service):
    import fcntl
    instance, adapter = worker(service)
    with instance.shared_lock.open('w') as lock:
        instance.shared_lock.chmod(0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError): instance.run_once()
    assert adapter.calls == []


def test_owned_public_runtime_directory_keeps_private_lock(service):
    instance, adapter = worker(service)
    parent = service.settings.root / 'shared-runtime'
    parent.mkdir(mode=0o755)
    instance.shared_lock = parent / 'desktop-worker.lock'
    assert instance.run_once()['status'] == 'SUCCEEDED'
    assert instance.shared_lock.stat().st_mode & 0o777 == 0o600


def test_other_writable_shared_directory_refuses_claim(service):
    instance, adapter = worker(service)
    parent = service.settings.root / 'shared-runtime'
    parent.mkdir(mode=0o700); parent.chmod(0o777)
    instance.shared_lock = parent / 'desktop-worker.lock'
    with pytest.raises(ValueError): instance.run_once()
    assert adapter.calls == []


@pytest.mark.parametrize('fault', [None, 'verify', 'pending'])
def test_usage_persists_without_turning_failed_execution_into_success(service, fault):
    instance, adapter = worker(service, fault)
    usage = {'available': True, 'totalTokens': 22}
    adapter.usage = lambda prepared: usage
    result = instance.run_once()
    assert result['usage'] == usage
    if fault == 'pending':
        assert result['quarantined'] and result['status'] == 'BLOCKED'
    else:
        state = service.view(result['taskId'])
        assert state['usage'] == usage
        assert state['status'] == ('UNVERIFIED' if fault else 'SUCCEEDED')
