"""CLI boundaries without VM/model actions; DB outcomes tested separately."""
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from backend import handoff_publish_operator as entry

TASK = '11111111-1111-1111-1111-111111111111'


@pytest.mark.parametrize('command,review', [('publish', 'a'*64), ('inspect', None)])
def test_routes_through_isolated_profile_and_disposes(monkeypatch, command, review):
    settings = SimpleNamespace(database_url='synthetic-db')
    profile = Mock(return_value=SimpleNamespace(settings=settings)); monkeypatch.setattr(entry, 'load_profile', profile)
    engine, sessions, service = Mock(), Mock(), Mock()
    monkeypatch.setattr(entry, 'database', Mock(return_value=(engine, sessions)))
    factory = Mock(return_value=service); monkeypatch.setattr(entry, 'TaskService', factory)
    publish, inspect = Mock(return_value={'status': 'SUCCEEDED'}), Mock(return_value={'status': 'UNVERIFIED'})
    monkeypatch.setattr(entry, 'publish_reviewed_task', publish); monkeypatch.setattr(entry, 'inspect_publication', inspect)
    result = entry.run(command, profile_path='/private/service.json', task_id=TASK, review_sha256=review)
    profile.assert_called_once_with('/private/service.json', kind='project-handoff')
    factory.assert_called_once_with(sessions, settings)
    if command == 'publish':
        publish.assert_called_once_with(service, TASK, review); inspect.assert_not_called()
    else:
        inspect.assert_called_once_with(service, TASK); publish.assert_not_called()
    engine.dispose.assert_called_once()


@pytest.mark.parametrize('command,task,review', [('publish', TASK, None), ('publish', TASK, '../a'),
    ('publish', TASK, 'A'*64), ('inspect', TASK, 'a'*64), ('publish', 'bad', 'a'*64), ('other', TASK, None)])
def test_invalid_input_has_no_profile_or_database_access(monkeypatch, command, task, review):
    profile = Mock(); monkeypatch.setattr(entry, 'load_profile', profile)
    with pytest.raises(ValueError): entry.run(command, profile_path='/unused', task_id=task, review_sha256=review)
    profile.assert_not_called()


def test_unknown_commit_result_is_not_retried_and_error_is_redacted(monkeypatch, capsys):
    run = Mock(side_effect=RuntimeError('postgres://secret-password@private'))
    monkeypatch.setattr(entry, 'run', run)
    assert entry.main(['publish', '--profile', '/unused', '--task', TASK, '--review-sha256', 'a'*64]) == 1
    output = capsys.readouterr().out
    assert 'secret-password' not in output and json.loads(output)['result'] == 'PUBLICATION_UNCONFIRMED'
    assert run.call_count == 1


def test_actual_cli_failure_is_nonzero_and_bounded():
    result = subprocess.run([sys.executable, '-m', 'backend.handoff_publish_operator', 'inspect',
        '--profile', '/nonexistent/private-service.json', '--task', TASK], capture_output=True, text=True, timeout=15)
    assert result.returncode == 1 and not result.stderr
    assert json.loads(result.stdout)['result'] == 'INSPECTION_UNCONFIRMED'
