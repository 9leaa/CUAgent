import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import func, select
import pytest
from backend.api import create_app
from backend.models import Event, Notification, Task
from backend.notifications import Inbox


def test_durable_stop_notice_repeated_stop_and_read_are_idempotent(service, payload):
    identity, _ = service.submit(payload, 'notify-stop')
    inbox = Inbox(service.sessions)
    assert inbox.listing()['items'] == []
    assert service.stop(identity) == 'STOPPED'
    service.stop(identity)
    item, = inbox.listing()['items']
    assert item['status_at_event'] == item['current_status'] == 'STOPPED'
    assert item['artifact_urls'] == [] and item['read_at'] is None
    with ThreadPoolExecutor(max_workers=3) as pool:
        acknowledgements = list(pool.map(lambda _: inbox.mark_read(item['id']), range(3)))
    assert acknowledgements[0] == acknowledgements[1] == acknowledgements[2]
    assert Inbox(service.sessions).listing(unread_only=True)['items'] == []
    assert len(inbox.listing()['items']) == 1


@pytest.mark.parametrize('status', ['FAILED', 'BLOCKED', 'UNVERIFIED'])
def test_failed_finish_notice_is_in_same_transaction_and_contains_no_source(service, payload, status):
    identity, _ = service.submit(payload, 'failure')
    task = service.claim('owner')
    service.finish(identity, task.owner, task.epoch, status, error_code='TEST_FAILURE')
    item, = Inbox(service.sessions).listing()['items']
    assert item['status_at_event'] == status
    assert item['error_code'] == 'TEST_FAILURE'
    assert item['artifact_urls'] == []
    assert payload['notes'][0]['content'] not in json.dumps(item, ensure_ascii=False)
    with service.sessions() as db:
        event = db.get(Event, item['event_id'])
        assert event.kind == 'finished' and event.data['status'] == status


def test_notification_and_terminal_event_rollback_together(service, payload):
    identity, _ = service.submit(payload, 'rollback')
    with pytest.raises(RuntimeError):
        with service.sessions.begin() as db:
            task = db.get(Task, identity)
            task.status = 'FAILED'
            service.event(db, task, 'finished', status='FAILED')
            db.flush()
            raise RuntimeError('transaction interrupted')
    assert Inbox(service.sessions).listing()['items'] == []
    with service.sessions() as db:
        assert db.get(Task, identity).status == 'QUEUED'
        assert db.scalar(select(func.count()).select_from(Event)) == 1


def test_history_after_resume_is_labelled_not_current_terminal(service, payload):
    identity, _ = service.submit(payload, 'resume')
    service.stop(identity)
    old, = Inbox(service.sessions).listing()['items']
    service.resume(identity)
    current, = Inbox(service.sessions).listing()['items']
    assert current['status_at_event'] == 'STOPPED' and current['current_status'] == 'QUEUED'
    assert current['artifact_urls'] == []
    service.stop(identity)
    rows = Inbox(service.sessions).listing(after=old['id'])['items']
    assert len(rows) == 1 and rows[0]['event_id'] != old['event_id']


def test_api_auth_cursor_read_persists_across_app_instances(service, payload):
    identity, _ = service.submit(payload, 'api-notice')
    service.stop(identity)
    headers = {'Authorization': 'Bearer ' + service.settings.api_token}
    with TestClient(create_app(service.settings)) as client:
        assert client.get('/notifications').status_code == 401
        response = client.get('/notifications', headers=headers).json()
        item, = response['items']
        assert client.get('/notifications', params={'after': response['next_cursor']}, headers=headers).json()['items'] == []
        assert client.get('/notifications', params={'limit': 101}, headers=headers).status_code == 422
        assert client.post('/notifications/' + str(item['id']) + '/read').status_code == 401
        assert client.post('/notifications/' + str(item['id']) + '/read', headers=headers).status_code == 200
        assert client.post('/notifications/999999/read', headers=headers).status_code == 404
    with TestClient(create_app(service.settings)) as client:
        assert client.get('/notifications', params={'unread_only': True}, headers=headers).json()['items'] == []
        assert client.get('/notifications', headers=headers).json()['items'][0]['read_at'] is not None


def test_success_links_only_for_success_current_state(service, payload):
    identity, _ = service.submit(payload, 'success-notice')
    # Synthetic state fixture tests inbox rendering, not business acceptance.
    with service.sessions.begin() as db:
        task = db.get(Task, identity)
        task.status = 'SUCCEEDED'
        service.event(db, task, 'finished', status='SUCCEEDED')
    item, = Inbox(service.sessions).listing()['items']
    assert len(item['artifact_urls']) == 2
    with service.sessions.begin() as db:
        db.get(Task, identity).status = 'UNVERIFIED'
    item, = Inbox(service.sessions).listing()['items']
    assert item['status_at_event'] == 'SUCCEEDED' and item['current_status'] == 'UNVERIFIED'
    assert item['artifact_urls'] == []
