"""Isolated PostgreSQL and synthetic Driver/review; no live VM/model."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.api import create_app
from backend.handoff_publication import publish_reviewed_task, prepare_publication
from backend.handoff_result import canonical
from backend.models import Task, Attempt, Event, Artifact, Resource, utcnow
from backend.notifications import Inbox
from backend.tests.test_handoff_publication import recorded
from backend.tests.test_handoff_operator import operator
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_review import context

pytestmark = pytest.mark.parametrize('evidence', [context()], indirect=True)


@pytest.fixture
def ready(service, operator):
    root, digest, _ = recorded(operator)
    prepared = prepare_publication(root, digest)
    service.settings = replace(service.settings, root=root.parent)
    (root / 'workspace').mkdir(mode=0o700, exist_ok=True)
    identity = root.name[3:]
    with service.sessions.begin() as db:
        resource = db.get(Resource, 'desktop'); resource.owner = resource.task_id = resource.expires_at = None
        task = Task(id=identity, idempotency_key='synthetic-p7', request_sha256=hashlib.sha256(canonical(prepared['submission'])).hexdigest(),
            payload=prepared['submission'], status='UNVERIFIED', error_code='DESKTOP_VERIFICATION_FAILED',
            run_dir=str(root), session_id=prepared['binding']['sessionId'], owner='worker', epoch=1, calls=prepared['rawCalls'])
        db.add(task); db.flush()
        db.add(Attempt(task_id=identity, owner='worker', epoch=1, finished_at=utcnow()))
        service.event(db, task, 'finished', status='UNVERIFIED', error_code=task.error_code)
        service.control(task, stopped=True)
    return root, digest, identity, prepared


def test_original_task_publication_downloads_and_preserves_failure(service, ready):
    root, digest, identity, prepared = ready
    from backend.handoff_publish_operator import inspect_publication
    before = inspect_publication(service, identity)
    assert before['status'] == 'UNVERIFIED' and not before['databasePublicationRecorded']
    assert before['publicationIntentPresent'] is False
    with TestClient(create_app(service.settings)) as client:
        assert client.get(f'/tasks/{identity}/artifacts/report.json').status_code == 401
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        assert client.get(f'/tasks/{identity}/artifacts/report.json').status_code == 404
    result = publish_reviewed_task(service, identity, digest)
    assert result['status'] == 'SUCCEEDED'
    inspected = inspect_publication(service, identity)
    assert inspected['databasePublicationRecorded'] and inspected['publicationIntentPresent']
    assert inspected['reviewFileSha256'] == digest and not inspected['retryAuthorized']
    assert not inspected['artifactBytesReverified']
    with service.sessions() as db:
        task = db.get(Task, identity)
        assert task.calls == prepared['rawCalls'] and task.session_id == prepared['binding']['sessionId']
        assert [e.data['status'] for e in db.scalars(select(Event).where(Event.kind == 'finished').order_by(Event.id))] == ['UNVERIFIED', 'SUCCEEDED']
        assert len(list(db.scalars(select(Artifact)))) == 3
        assert len(list(db.scalars(select(Attempt)))) == 1
    notices = Inbox(service.sessions).listing()['items']
    assert len(notices) == 2 and notices[0]['artifact_urls'] == [] and len(notices[1]['artifact_urls']) == 3
    assert all(n['read_at'] is None for n in notices)
    with TestClient(create_app(service.settings)) as client:
        client.headers['Authorization'] = 'Bearer ' + service.settings.api_token
        for name, raw in prepared['files'].items():
            response = client.get(f'/tasks/{identity}/artifacts/{name}')
            assert response.status_code == 200 and response.content == raw
        (root / 'workspace' / 'document.txt').write_bytes(b'changed')
        assert client.get(f'/tasks/{identity}/artifacts/document.txt').status_code == 409
    with pytest.raises(ValueError): publish_reviewed_task(service, identity, digest)


@pytest.mark.parametrize('fault', ['status', 'owner', 'epoch', 'session', 'calls', 'hash', 'payload', 'active_attempt', 'resource', 'control', 'run'])
def test_wrong_original_state_rejected_before_publication(service, ready, fault):
    root, digest, identity, _ = ready
    with service.sessions.begin() as db:
        task = db.get(Task, identity)
        if fault == 'status': task.status = 'STOPPED'
        elif fault == 'owner': task.owner = 'other'
        elif fault == 'epoch': task.epoch = 2
        elif fault == 'session': task.session_id = 'other'
        elif fault == 'calls': task.calls += 1
        elif fault == 'hash': task.request_sha256 = '0'*64
        elif fault == 'payload': task.payload = dict(task.payload, project='changed')
        elif fault == 'active_attempt': db.scalar(select(Attempt)).finished_at = None
        elif fault == 'resource': db.get(Resource, 'desktop').owner = 'other'
        elif fault == 'run': task.run_dir = str(root.parent)
        else:
            path = service.settings.root / 'controls' / (identity + '.json')
            value = json.loads(path.read_bytes()); value['stopped'] = False; path.write_bytes(canonical(value))
    with pytest.raises(ValueError): publish_reviewed_task(service, identity, digest)
    assert not (root / 'handoff-publication-intent.json').exists()
    with service.sessions() as db: assert list(db.scalars(select(Artifact))) == []


def test_file_failure_rolls_back_database_and_retains_intent(service, ready):
    root, digest, identity, _ = ready
    from backend.desktop_collect import save_exclusive
    def fail(path, raw):
        if path.name == 'result.txt': raise OSError('synthetic disk failure')
        save_exclusive(path, raw)
    with patch('backend.desktop_collect.save_exclusive', side_effect=fail):
        with pytest.raises(OSError): publish_reviewed_task(service, identity, digest)
    assert (root / 'handoff-publication-intent.json').exists()
    assert (root / 'workspace' / 'document.txt').exists()
    with service.sessions() as db:
        assert db.get(Task, identity).status == 'UNVERIFIED'
        assert list(db.scalars(select(Artifact))) == []
    with pytest.raises(FileExistsError): publish_reviewed_task(service, identity, digest)


def test_ordinary_finish_cannot_bypass_independent_review(service, ready):
    _, _, identity, _ = ready
    from datetime import timedelta
    with service.sessions.begin() as db:
        r = db.get(Resource, 'desktop'); r.owner = 'worker'; r.task_id = identity; r.epoch = 1; r.expires_at = utcnow() + timedelta(minutes=1)
    with pytest.raises(ValueError, match='HANDOFF_REVIEWED_PUBLICATION_REQUIRED'):
        service.finish(identity, 'worker', 1, 'SUCCEEDED', result={'status': 'SUCCEEDED'})


def test_concurrent_publishers_register_only_one_result(service, ready):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    root, digest, identity, _ = ready
    barrier = threading.Barrier(2)
    def publish():
        barrier.wait(timeout=5)
        try: return publish_reviewed_task(service, identity, digest)['status']
        except ValueError: return 'REJECTED'
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(publish), pool.submit(publish)
        assert sorted([a.result(timeout=30), b.result(timeout=30)]) == ['REJECTED', 'SUCCEEDED']
    with service.sessions() as db:
        assert len(list(db.scalars(select(Artifact)))) == 3
        assert len(list(db.scalars(select(Event).where(Event.kind == 'handoff_published')))) == 1
    assert len(Inbox(service.sessions).listing()['items']) == 2


def test_database_failure_leaves_no_success_and_no_automatic_retry(service, ready):
    root, digest, identity, _ = ready
    with patch.object(service, 'event', side_effect=RuntimeError('synthetic transaction failure')):
        with pytest.raises(RuntimeError): publish_reviewed_task(service, identity, digest)
    assert (root / 'handoff-publication-intent.json').exists()
    with service.sessions() as db:
        assert db.get(Task, identity).status == 'UNVERIFIED'
        assert list(db.scalars(select(Artifact))) == []
        assert list(db.scalars(select(Event).where(Event.kind == 'handoff_published'))) == []
    assert len(Inbox(service.sessions).listing()['items']) == 1
    from backend.handoff_publish_operator import inspect_publication
    inspected = inspect_publication(service, identity)
    assert inspected['publicationIntentPresent'] and not inspected['databasePublicationRecorded']
    assert inspected['artifacts'] == {} and not inspected['retryAuthorized']
    with pytest.raises(FileExistsError): publish_reviewed_task(service, identity, digest)
