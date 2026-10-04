"""Synthetic evidence/isolated DB tests, not VM acceptance."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from backend.desktop_collect import save_exclusive
from backend.desktop_preparation import confirm_preparation_closed
from backend.desktop_worker import DesktopWorker


def stage(root, home, task, guest_state='closed'):
    root.mkdir(mode=0o700)
    (home / 'profiles/desktop').mkdir(mode=0o700, parents=True)
    home.chmod(0o700)
    original = b'[]\n'
    identity = dict(version=1, runId=root.name, owner=task.owner, epoch=task.epoch)
    ready = dict(binding=identity, activated=False, controlHost='127.0.0.1', controlPort=19001,
                 pid=808, modelUrl='http://192.168.64.3:8766', controlToken='c' * 43, modelToken='m' * 43)
    target = home / 'profiles/desktop/cordis.patch.yml'
    save_exclusive(target, original)
    save_exclusive(root / 'profile-before.yml', original)
    records = {
        'profile-plan.json': dict(version=1, root=str(root), home=str(home), target=str(target),
                                  beforeSha256=hashlib.sha256(original).hexdigest()),
        'desktop-guest-start-intent.json': {'binding': identity},
        'guest-private-receipt.json': ready,
        'desktop-prepare-cleanup-intent.json': identity,
        'desktop-prepare-cleanup.json': dict(binding=identity, closed=True, stopped=True,
                                           active=False, rawCalls=0, pendingCalls=0),
        'desktop-prepare-failure.json': dict(taskId=task.id, runId=root.name, stage='tunnel-start',
                                           cleanupConfirmed=True, guestStartAttempted=True, guestReceiptPresent=True),
    }
    if guest_state == 'not-started':
        records = {'profile-plan.json': records['profile-plan.json'],
                   'desktop-prepare-failure.json': dict(taskId=task.id, runId=root.name,
                       stage='tunnel-port-preflight', binding=identity, guestNotStarted=True,
                       cleanupConfirmed=False, guestStartAttempted=False, guestReceiptPresent=False)}
    for name, value in records.items(): save_exclusive(root / name, json.dumps(value).encode())


@pytest.fixture
def evidence(tmp_path):
    task = SimpleNamespace(id='11111111-1111-1111-1111-111111111111',
                           owner='22222222-2222-2222-2222-222222222222', epoch=1)
    root, home = tmp_path / ('p2-' + task.id), tmp_path / 'home'
    stage(root, home, task)
    return dict(root=root, home=home, task=task)


def test_bound_closed_guest_original_profile_proof(evidence):
    proof = confirm_preparation_closed(**evidence)
    assert proof.run == evidence['root'] and proof.owner == evidence['task'].owner


@pytest.mark.parametrize('name', ['app-activate-stop-intent.json', 'profile-apply-intent.json',
    'desktop-start-intent.json', 'desktop-session-start-intent.json', 'create-request.json',
    'prompt-request.json', 'profile-restore-receipt.json'])
def test_any_start_intent_including_broken_symlink_refuses_proof(evidence, name):
    (evidence['root'] / name).symlink_to('nonexistent')
    with pytest.raises(ValueError): confirm_preparation_closed(**evidence)


@pytest.mark.parametrize('fault', ['profile-changed', 'receipt-missing', 'wrong-epoch', 'boolean-epoch',
    'nonzero-raw', 'extra-field', 'failed-cleanup', 'wrong-stage', 'public-receipt', 'wrong-launch'])
def test_missing_changed_or_unsafe_proof_rejected(evidence, fault):
    root, home = evidence['root'], evidence['home']
    if fault == 'profile-changed': (home / 'profiles/desktop/cordis.patch.yml').write_bytes(b'changed')
    elif fault == 'receipt-missing': (root / 'desktop-prepare-cleanup.json').unlink()
    elif fault == 'public-receipt': (root / 'desktop-prepare-cleanup.json').chmod(0o644)
    else:
        name = ('desktop-prepare-failure.json' if fault in ('failed-cleanup', 'wrong-stage') else
                'desktop-guest-start-intent.json' if fault == 'wrong-launch' else 'desktop-prepare-cleanup.json')
        path = root / name
        value = json.loads(path.read_text())
        if fault in ('wrong-epoch', 'boolean-epoch', 'wrong-launch'):
            value['binding']['epoch'] = True if fault == 'boolean-epoch' else 2
        if fault == 'nonzero-raw': value['rawCalls'] = 1
        if fault == 'extra-field': value['extra'] = True
        if fault == 'failed-cleanup': value['cleanupConfirmed'] = False
        if fault == 'wrong-stage': value['stage'] = 'guest-bootstrap'
        path.write_text(json.dumps(value))
    with pytest.raises((ValueError, FileNotFoundError)): confirm_preparation_closed(**evidence)


class FailedPreparationAdapter:
    def __init__(self, service, fault=None, guest_state='closed'):
        self.service, self.fault = service, fault
        self.guest_state = guest_state
        self.start, self.restore, self.cancel = Mock(), Mock(), Mock()

    def prepare(self, task):
        self.task = task
        self.root = self.service.settings.root / ('p2-' + task.id)
        self.home = self.service.settings.root / 'official-home'
        stage(self.root, self.home, task, self.guest_state)
        if self.fault == 'stop': self.service.stop(task.id)
        raise RuntimeError('synthetic preparation failure')

    def confirm_prepare_failure(self, task):
        proof = confirm_preparation_closed(root=self.root, home=self.home, task=task, guest_state=self.guest_state)
        if self.fault == 'wrong-proof': return replace(proof, epoch=proof.epoch + 1)
        if self.fault == 'missing-proof': raise ValueError('missing')
        if self.fault == 'owner-lost':
            from datetime import timedelta
            from sqlalchemy import update
            from backend.models import Resource, utcnow
            with self.service.sessions.begin() as db:
                db.execute(update(Resource).values(expires_at=utcnow() - timedelta(seconds=1)))
        return proof


@pytest.mark.parametrize('fault', [None, 'stop', 'wrong-proof', 'missing-proof', 'owner-lost', 'finish-error'])
@pytest.mark.parametrize('guest_state', ['closed', 'not-started'])
def test_worker_settles_only_confirmed_original_preparation(service, fault, monkeypatch, guest_state):
    task = service.submit({'kind': 'desktop-textedit', 'lines': ['synthetic']}, 'prep-failure')
    adapter = FailedPreparationAdapter(service, fault, guest_state)
    worker = DesktopWorker(service, adapter, shared_lock=service.settings.root / 'desktop-worker.lock')
    if fault == 'finish-error': monkeypatch.setattr(service, 'finish', Mock(side_effect=RuntimeError('DB unavailable')))
    result = worker.run_once()
    settled = fault in (None, 'stop')
    assert result['quarantined'] is (not settled)
    assert result['restoreConfirmed'] is settled
    assert result['status'] == ('FAILED' if fault is None else 'STOPPED' if fault == 'stop' else 'BLOCKED')
    view = service.view(result['taskId'])
    assert not view['artifacts']
    assert result['usage'] == {'available': False}
    if settled:
        assert result['preparationCleanupConfirmed'] is (guest_state == 'closed')
        assert result['guestNotStarted'] is (guest_state == 'not-started')
        assert result['revocation']['guestRevoked'] is (guest_state == 'closed')
        assert result['profileUnchanged'] and result['restoreRequired'] is False
        assert result['appSwitchAttempted'] is False
        assert view['status'] == result['status']
        assert json.loads((service.settings.root / 'controls' / (result['taskId'] + '.json')).read_text())['stopped']
        assert worker.run_once() is None
    else:
        with pytest.raises(RuntimeError, match='QUARANTINED'): worker.run_once()
    adapter.start.assert_not_called()
    adapter.restore.assert_not_called()
    adapter.cancel.assert_not_called()


@pytest.fixture
def not_started(tmp_path):
    task = SimpleNamespace(id='11111111-1111-1111-1111-111111111111',
                           owner='22222222-2222-2222-2222-222222222222', epoch=1)
    root, home = tmp_path / ('p2-' + task.id), tmp_path / 'home'
    stage(root, home, task, 'not-started')
    return dict(root=root, home=home, task=task, guest_state='not-started')


def test_not_started_proof_requires_explicit_mode(not_started):
    assert confirm_preparation_closed(**not_started).guest_state == 'not-started'
    with pytest.raises(FileNotFoundError):
        confirm_preparation_closed(**{k:v for k,v in not_started.items() if k != 'guest_state'})


@pytest.mark.parametrize('name', ['desktop-guest-start-intent.json', 'guest-private-receipt.json',
    'desktop-tunnel-intent.json', 'desktop-prepare-cleanup-intent.json', 'desktop-prepare-cleanup.json',
    'c0-connection.json', 'app-activate-stop-intent.json', 'profile-apply-intent.json', 'prompt-request.json'])
def test_not_started_rejects_any_launch_or_action_even_broken_link(not_started, name):
    (not_started['root'] / name).symlink_to('missing')
    with pytest.raises(ValueError): confirm_preparation_closed(**not_started)


@pytest.mark.parametrize('field,value', [('stage','guest-bootstrap'), ('stage','profile-prepare'),
    ('guestNotStarted',False), ('guestNotStarted',1), ('guestStartAttempted',True),
    ('guestStartAttempted',0), ('guestReceiptPresent',True), ('cleanupConfirmed',True),
    ('binding',None)])
def test_not_started_rejects_missing_or_contradictory_proof(not_started, field, value):
    path = not_started['root'] / 'desktop-prepare-failure.json'
    data = json.loads(path.read_text()); data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError): confirm_preparation_closed(**not_started)


def test_not_started_rejects_profile_change(not_started):
    (not_started['home'] / 'profiles/desktop/cordis.patch.yml').write_bytes(b'changed')
    with pytest.raises(ValueError): confirm_preparation_closed(**not_started)


def test_heartbeat_loss_during_prepare_forbids_settlement_even_with_receipt(service, monkeypatch):
    import threading
    service.submit({'kind': 'desktop-textedit', 'lines': ['synthetic']}, 'prep-loss')
    adapter = FailedPreparationAdapter(service)
    pulse_seen = threading.Event()
    original = adapter.prepare
    def prepare(task):
        assert pulse_seen.wait(5)
        return original(task)
    def failed_heartbeat(*args, **kwargs):
        pulse_seen.set()
        raise RuntimeError('ownership unknown')
    adapter.prepare = prepare
    adapter.confirm_prepare_failure = Mock(side_effect=AssertionError('must not settle'))
    monkeypatch.setattr(service, 'heartbeat', failed_heartbeat)
    worker = DesktopWorker(service, adapter, shared_lock=service.settings.root / 'desktop-worker.lock')
    result = worker.run_once()
    assert result['status'] == 'BLOCKED' and result['quarantined']
    adapter.confirm_prepare_failure.assert_not_called()
