from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock
from fastapi.testclient import TestClient
import pytest
from backend.api import create_app
from backend.schedule_runtime import QuotaPermit, WorkflowCollector

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)


def record():
    return dict(version=1, scheduleId='plan', dueAt=NOW.isoformat(), checkedAt=NOW.isoformat(),
                expiresAt=(NOW + timedelta(minutes=5)).isoformat(), ordinaryUsageAllowed=True,
                remainingPercent=92, creditsBalance='62494.0260570000', resetCardsUsed=0)


def save(path, value):
    path.write_text(json.dumps(value)); path.chmod(0o600)


def test_permit_is_specific_private_fresh_and_can_be_revoked(tmp_path):
    path = tmp_path / 'permit.json'
    permit = QuotaPermit(path)
    assert not permit('plan', NOW, NOW)
    save(path, record())
    assert permit('plan', NOW, NOW)
    assert not permit('other', NOW, NOW)
    assert not permit('plan', NOW + timedelta(days=1), NOW)
    assert not permit('plan', NOW, NOW + timedelta(minutes=5))
    value = record(); value['ordinaryUsageAllowed'] = False; save(path, value)
    assert not permit('plan', NOW, NOW)


@pytest.mark.parametrize('change', [dict(remainingPercent=5), dict(remainingPercent=True),
    dict(remainingPercent=float('nan')), dict(creditsBalance='62493'), dict(resetCardsUsed=1),
    dict(resetCardsUsed=False), dict(checkedAt=(NOW + timedelta(seconds=1)).isoformat()),
    dict(expiresAt=(NOW + timedelta(minutes=6)).isoformat()), dict(dueAt='2026-10-03T00:00:00')])
def test_invalid_budget_or_time_never_authorizes(tmp_path, change):
    path = tmp_path / 'permit.json'; save(path, {**record(), **change})
    assert not QuotaPermit(path)('plan', NOW, NOW)


def test_permit_rejects_symlink_public_permissions_and_partial_json(tmp_path):
    path = tmp_path / 'permit.json'; target = tmp_path / 'source.json'; save(target, record())
    path.symlink_to(target)
    assert not QuotaPermit(path)('plan', NOW, NOW)
    path.unlink(); save(path, record()); path.chmod(0o644)
    assert not QuotaPermit(path)('plan', NOW, NOW)
    path.chmod(0o600); path.write_text('{')
    assert not QuotaPermit(path)('plan', NOW, NOW)


def test_collector_uses_only_fixed_branch_repository_and_occurrence_window(monkeypatch):
    git = Mock(return_value='b'*40 + '\n')
    project, operations = Mock(return_value={'workflow': 'project-changes'}), Mock(return_value={'workflow': 'task-operations'})
    monkeypatch.setattr('backend.schedule_runtime.subprocess.check_output', git)
    monkeypatch.setattr('backend.schedule_runtime.project_snapshot', project)
    monkeypatch.setattr('backend.schedule_runtime.collect_operations', operations)
    sessions = object()
    ticket = {'config': {'branch': 'p5-personal-workflows', 'timezone': 'Asia/Shanghai'}, 'dueAt': NOW, 'lastCommit': 'a'*40}
    result = WorkflowCollector(sessions)(ticket)
    assert [r['workflow'] for r in result] == ['project-changes', 'task-operations']
    assert git.call_args.args[0] == ['git', 'rev-parse', '--verify', 'refs/heads/p5-personal-workflows']
    project.assert_called_once_with('a'*40, 'b'*40, '2026-10-03')
    operations.assert_called_once_with(sessions, NOW-timedelta(days=1), NOW, '2026-10-03')
    ticket['config']['branch'] = '--all'
    with pytest.raises(ValueError): WorkflowCollector(sessions)(ticket)
    assert git.call_count == 1


def test_schedule_api_create_query_pause_survives_restart_without_grant(service):
    start = datetime.now(timezone.utc) + timedelta(minutes=1)
    body = dict(startAt=start.isoformat(), timezone='UTC', runs=1,
                branch='p5-personal-workflows', baselineCommit='a'*40)
    headers = {'Authorization': 'Bearer ' + service.settings.api_token, 'Idempotency-Key': 'schedule-api'}
    with TestClient(create_app(service.settings)) as client:
        assert client.get('/schedules').status_code == 401
        response = client.post('/schedules', json=body, headers=headers)
        assert response.status_code == 201, response.text
        identity = response.json()['id']
        assert client.post('/schedules', json=body, headers=headers).json() == {'id': identity, 'created': False}
        assert client.post('/schedules', json={**body, 'runs': 2}, headers=headers).status_code == 409
        assert client.get('/schedules/' + identity, headers=headers).json()['items'] == []
        assert client.post('/schedules/' + identity + '/pause', headers=headers).json()['status'] == 'PAUSED'
        assert client.post('/schedules', json={**body, 'runs': 8}, headers=headers).status_code == 422
        assert client.post('/schedules', json={**body, 'startAt': '2020-01-01T00:00:00+00:00'},
                           headers={**headers, 'Idempotency-Key': 'past-plan'}).status_code == 422
    with TestClient(create_app(service.settings)) as client:
        item, = client.get('/schedules', headers=headers).json()['items']
        assert item['id'] == identity and item['status'] == 'PAUSED' and item['occurrences'] == 0
    assert not (service.settings.root / 'scheduler-permit.json').exists()
