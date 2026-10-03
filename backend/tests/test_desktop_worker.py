"""Synthetic adapter validates orchestration, not real GUI or model behavior."""
import hashlib
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


def test_verification_failure_does_not_deliver_artifacts(service):
    instance, adapter = worker(service, 'verify')
    result = instance.run_once()
    assert result['status'] == 'UNVERIFIED' and result['restoreConfirmed']
    assert service.view(result['taskId'])['artifacts'] == []


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
