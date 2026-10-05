"""Explicit routing only: isolated DB, no model or VM execution."""
from dataclasses import replace
from unittest.mock import Mock
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.api import create_app
from backend.desktop_service import load_profile, create_desktop_app
from backend.desktop_worker import DesktopWorker
from backend.models import Task
from backend.handoff_acceptance import load_acceptance_case
from backend.tests.test_desktop_service import profile
from backend.tests.test_desktop_operator import operator_files


def body():
    return load_acceptance_case('normal')[0]['input']


def test_default_and_p6_api_refuse_handoff(service):
    for settings in [service.settings, replace(service.settings, desktop_tasks_enabled=True)]:
        with TestClient(create_app(settings)) as client:
            client.headers['Authorization'] = 'Bearer ' + settings.api_token
            assert client.post('/handoff-tasks', json=body(), headers={'Idempotency-Key': 'one'}).status_code == 503
    with service.sessions() as db: assert list(db.scalars(select(Task))) == []


def test_explicit_api_idempotency_validation_and_separation(service):
    with TestClient(create_app(replace(service.settings, handoff_tasks_enabled=True))) as client:
        headers = {'Idempotency-Key': 'one'}
        assert client.post('/handoff-tasks', json=body(), headers=headers).status_code == 401
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        first = client.post('/handoff-tasks', json=body(), headers=headers)
        assert first.status_code == 201
        identity = first.json()['id']
        assert client.post('/handoff-tasks', json=body(), headers=headers).json() == {'id': identity, 'created': False}
        assert client.post('/handoff-tasks', json=dict(body(), project='changed'), headers=headers).status_code == 409
        assert client.post('/handoff-tasks', json=dict(body(), tool='shell'), headers=headers).status_code == 422
        assert client.post('/handoff-tasks', json=body(), headers={'Idempotency-Key': '../one'}).status_code == 422
        for endpoint in ['/tasks', '/desktop-tasks']:
            assert client.post(endpoint, json=body(), headers=headers).status_code == 422
        assert client.post(f'/tasks/{identity}/stop').json()['status'] == 'STOPPED'
        assert client.post(f'/tasks/{identity}/resume').status_code == 409


def test_three_kinds_share_lock_without_cross_claim(service, payload):
    handoff, _ = service.submit(body(), 'p7')
    desktop, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['P6']}, 'p6')
    report, _ = service.submit(payload, 'p5')
    for kind, identity in [('daily-report', report), ('desktop-textedit', desktop), ('project-handoff', handoff)]:
        claimed = service.claim(str(uuid.uuid4()), kind=kind)
        assert claimed.id == identity
        assert service.claim(str(uuid.uuid4()), kind='project-handoff') is None
        service.finish(identity, claimed.owner, claimed.epoch, 'STOPPED')


def test_worker_explicit_kind_selects_only_target(service, tmp_path):
    identity, _ = service.submit(body(), 'p7')
    worker = DesktopWorker(service, Mock(), shared_lock=tmp_path / 'worker.lock', kind='project-handoff')
    worker.execute = Mock(side_effect=lambda task: task.id)
    assert worker.run_once(task_id=identity) == identity
    assert worker.execute.call_count == 1


def test_isolated_service_only_allows_selected_creation(profile):
    before = profile.read_bytes()
    loaded = load_profile(profile, kind='project-handoff')
    assert loaded.settings.handoff_tasks_enabled and not loaded.settings.desktop_tasks_enabled
    with TestClient(create_desktop_app(loaded)) as client:
        client.headers['Authorization'] = 'Bearer ' + loaded.settings.api_token
        assert client.post('/handoff-tasks', json=body(), headers={'Idempotency-Key': 'p7'}).status_code == 201
        for endpoint in ['/desktop-tasks', '/tasks', '/schedules', '/batches', '/handoff-publish']:
            assert client.post(endpoint, json={}).status_code == 409
    assert profile.read_bytes() == before
    assert not load_profile(profile).settings.handoff_tasks_enabled


@pytest.mark.parametrize('kind', ['daily-report', 'other', None])
def test_invalid_worker_and_profile_kind_refused_before_io(kind):
    with pytest.raises(ValueError): DesktopWorker(None, None, shared_lock='/unused', kind=kind)
    with pytest.raises(ValueError): load_profile('/unused', kind=kind)


def test_operator_selects_handoff_adapter_and_original_target_only(operator_files, monkeypatch):
    import hashlib
    import json
    from backend import desktop_operator as entry, handoff_adapter
    from backend.handoff_result import canonical
    from backend.tests.test_desktop_worker import Adapter
    args, service, first = operator_files
    with service.sessions.begin() as db:
        task = db.get(Task, args['task_id']); task.payload = body()
        task.request_sha256 = hashlib.sha256(canonical(body())).hexdigest()
    gate = Mock(return_value=True)
    monkeypatch.setattr(entry, 'LiveGate', lambda *_: gate)
    p6 = Mock(side_effect=AssertionError('P6 adapter must not run'))
    monkeypatch.setattr(entry, 'DesktopTaskAdapter', p6)
    class PendingReview(Adapter):
        def verify(self, prepared):
            raise ValueError('HANDOFF_SEMANTIC_REVIEW_REQUIRED')
    factory = Mock(side_effect=lambda svc, settings, execution_gate: PendingReview(svc))
    monkeypatch.setattr(handoff_adapter, 'HandoffTaskAdapter', factory)
    outcome = entry.worker_once(**args, kind='project-handoff')
    assert outcome['outcome']['status'] == 'UNVERIFIED'
    assert outcome['outcome']['restoreConfirmed']
    assert service.view(first)['status'] == 'QUEUED'
    assert service.view(args['task_id'])['kind'] == 'project-handoff'
    p6.assert_not_called(); assert factory.call_count == 1
    intent = json.loads((args['profile_path'].parent / ('desktop-launch-' + args['task_id'] + '.json')).read_bytes())
    assert intent['kind'] == 'project-handoff'
    with pytest.raises(ValueError, match='UNATTEMPTED'): entry.worker_once(**args, kind='project-handoff')


def test_p7_operator_cannot_claim_p6_target(operator_files, monkeypatch):
    from backend import desktop_operator as entry, handoff_adapter
    args, service, _ = operator_files
    gate, adapter = Mock(return_value=True), Mock()
    monkeypatch.setattr(entry, 'LiveGate', lambda *_: gate)
    monkeypatch.setattr(handoff_adapter, 'HandoffTaskAdapter', lambda *a, **kw: adapter)
    with pytest.raises(ValueError, match='UNATTEMPTED'): entry.worker_once(**args, kind='project-handoff')
    gate.assert_not_called(); adapter.prepare.assert_not_called()
    assert service.view(args['task_id'])['status'] == 'QUEUED'
