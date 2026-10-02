from pathlib import Path
from types import SimpleNamespace
import subprocess
from unittest.mock import patch
import pytest
from backend.worker import Worker


def worker():
    result = object.__new__(Worker)
    result.settings = SimpleNamespace(cookie_file=Path('/private/cookie'))
    return result


def test_readonly_rpc_retries_same_original_identity():
    failed = subprocess.CompletedProcess([], 1, '', 'private failure')
    passed = subprocess.CompletedProcess([], 0, '{"sessionId":"original","terminal":false}', '')
    with patch('backend.worker.subprocess.run', side_effect=[failed, passed]) as run, patch('backend.worker.time.sleep'):
        assert worker().rpc_process('inspect', '/original/run')['sessionId'] == 'original'
        assert run.call_count == 2
        assert run.call_args_list[0] == run.call_args_list[1]


@pytest.mark.parametrize('mode', ['start', 'start-existing', 'create-only', 'continue', 'activate', 'rebind', 'cancel', 'restore'])
def test_effectful_rpc_timeout_never_replays(mode):
    with patch('backend.worker.subprocess.run', side_effect=subprocess.TimeoutExpired('private-command', 55)) as run:
        with pytest.raises(RuntimeError, match='^DESKTOP_' + mode.upper() + '_FAILED$'):
            worker().rpc_process(mode, '/original/run')
        assert run.call_count == 1


def test_readonly_rpc_has_bounded_retries_and_redacted_error():
    with patch('backend.worker.subprocess.run', side_effect=subprocess.TimeoutExpired('secret', 55)) as run, patch('backend.worker.time.sleep'):
        with pytest.raises(RuntimeError, match='^DESKTOP_POLL_FAILED$'):
            worker().rpc_process('poll', '/original/run')
        assert run.call_count == 3


def test_local_revocation_stops_current_owner_but_cannot_fence_new_owner(tmp_path):
    import json
    from backend.control import write_control
    instance = worker()
    instance.settings = SimpleNamespace(root=tmp_path)
    instance.owner = 'old-owner'
    task = SimpleNamespace(id='task', epoch=1)
    path = tmp_path / 'controls/task.json'
    write_control(path, run_id='p2-task', epoch=1, owner='old-owner', expires_at=9999999999999)
    assert instance.revoke_local(task)
    assert json.loads(path.read_text())['stopped'] is True
    write_control(path, run_id='p2-task', epoch=2, owner='new-owner', expires_at=9999999999999)
    newer = path.read_bytes()
    assert instance.revoke_local(task) is False
    assert path.read_bytes() == newer


@pytest.mark.parametrize('terminal', [True, False])
def test_stop_queries_fresh_state_before_cancelling(tmp_path, terminal):
    instance = worker()
    with patch.object(instance, 'rpc_process', return_value={'exists': True, 'terminal': terminal}) as rpc:
        assert instance.stop_remote(tmp_path) is (not terminal)
        assert [call.args[0] for call in rpc.call_args_list] == (['inspect'] if terminal else ['inspect', 'cancel'])


def test_stop_missing_session_is_unknown_not_replayed(tmp_path):
    instance = worker()
    with patch.object(instance, 'rpc_process', return_value={'exists': False}) as rpc:
        with pytest.raises(RuntimeError, match='STOP_SESSION_MISSING_NO_REPLAY'):
            instance.stop_remote(tmp_path)
        assert rpc.call_count == 1


def activation_fixture(tmp_path):
    import json
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (tmp_path / 'approval.json').write_text(json.dumps({
        'runId': 'run', 'sessionId': 'original',
        'ledgerPath': str(tmp_path / 'calls.jsonl'), 'workspaceRoot': str(workspace)}))
    instance = worker()
    instance.settings = SimpleNamespace(base_tasks=Path('/base/tasks.json'))
    return instance


def test_activation_recovery_inspects_before_and_after_unique_rebind(tmp_path):
    instance = activation_fixture(tmp_path)
    missing = {'sessionId': 'original', 'exists': False}
    with patch.object(instance, 'rpc_process', side_effect=[missing, {}, missing]) as rpc:
        instance.recover_activation(tmp_path, None)
        assert [call.args[0] for call in rpc.call_args_list] == ['inspect', 'rebind', 'inspect']
    assert len(list(tmp_path.glob('backend-activation-reconciled-*.json'))) == 1


@pytest.mark.parametrize('name', ['create-request.json', 'session-created.json', 'model-selected.json',
                                'prompt-request.json', 'prompt-response.json', 'continuation-request.json'])
def test_activation_with_any_execution_intent_never_rebinds(tmp_path, name):
    instance = activation_fixture(tmp_path)
    (tmp_path / name).write_text('{}')
    with patch.object(instance, 'rpc_process') as rpc:
        with pytest.raises(RuntimeError, match='ACTIVATION_HAS_EXECUTION_INTENT'):
            instance.recover_activation(tmp_path, None)
        rpc.assert_not_called()


@pytest.mark.parametrize('state', [{}, {'exists': False}, {'sessionId': 'foreign', 'exists': False},
                                 {'sessionId': 'original', 'exists': True}])
def test_activation_requires_authoritative_same_session_absence(tmp_path, state):
    instance = activation_fixture(tmp_path)
    with patch.object(instance, 'rpc_process', return_value=state) as rpc:
        with pytest.raises(RuntimeError, match='ACTIVATION_SESSION_ABSENCE_UNPROVEN'):
            instance.recover_activation(tmp_path, None)
        assert rpc.call_count == 1


def test_activation_existing_artifact_rejected_before_rpc(tmp_path):
    instance = activation_fixture(tmp_path)
    (tmp_path / 'workspace/report.json').write_text('{}')
    with patch.object(instance, 'rpc_process') as rpc:
        with pytest.raises(RuntimeError, match='ACTIVATION_HAS_EXECUTION_EVIDENCE'):
            instance.recover_activation(tmp_path, None)
        rpc.assert_not_called()


def test_activation_rebind_failure_never_repeated(tmp_path):
    instance = activation_fixture(tmp_path)
    with patch.object(instance, 'rpc_process', side_effect=[
        {'sessionId': 'original', 'exists': False}, RuntimeError('DESKTOP_REBIND_FAILED')]) as rpc:
        with pytest.raises(RuntimeError, match='DESKTOP_REBIND_FAILED'):
            instance.recover_activation(tmp_path, None)
        assert [call.args[0] for call in rpc.call_args_list] == ['inspect', 'rebind']


@pytest.mark.parametrize('change', ['session', 'artifact', 'intent'])
def test_activation_rechecks_after_rebind(tmp_path, change):
    instance = activation_fixture(tmp_path)
    inspections = 0
    def rpc(mode, *args):
        nonlocal inspections
        if mode == 'rebind':
            if change == 'artifact':
                (tmp_path / 'workspace/report.json').write_text('{}')
            if change == 'intent':
                (tmp_path / 'prompt-request.json').write_text('{}')
            return {}
        inspections += 1
        return {'sessionId': 'original', 'exists': change == 'session' and inspections == 2}
    with patch.object(instance, 'rpc_process', side_effect=rpc):
        with pytest.raises(RuntimeError, match='ACTIVATION_'):
            instance.recover_activation(tmp_path, None)
    assert not list(tmp_path.glob('backend-activation-reconciled-*.json'))


def test_activation_rejects_audit_even_without_dispatch(tmp_path):
    import json
    instance = activation_fixture(tmp_path)
    (tmp_path / 'calls.jsonl').write_text(json.dumps({
        'runId': 'run', 'sessionId': 'original', 'event': 'request'}) + '\n')
    with patch.object(instance, 'rpc_process') as rpc:
        with pytest.raises(RuntimeError, match='ACTIVATION_HAS_EXECUTION_EVIDENCE'):
            instance.recover_activation(tmp_path, None)
        rpc.assert_not_called()
