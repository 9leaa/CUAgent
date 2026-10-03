"""Worker branch integration with fake RPC/DB, not real-model evidence."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from backend.worker import Worker


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    worker = object.__new__(Worker)
    worker.owner = 'owner'
    worker.settings = SimpleNamespace(base_tasks=tmp_path / 'base.json', root=tmp_path)
    worker.service = Mock()
    worker.service.heartbeat.return_value = False
    worker.prepare_task = Mock(return_value=tmp_path)
    worker.revoke_local = Mock(return_value=True)
    task = SimpleNamespace(id='task', epoch=2, checkpoint=None, release_at=None)
    for name in ('active-tasks.json', 'create-request.json', 'prompt-request.json'):
        (tmp_path / name).write_text('{}')
    monkeypatch.setattr('backend.worker.snapshot', lambda *_: {'used': 0})
    verification = Mock(return_value={'status': 'SUCCEEDED'})
    monkeypatch.setattr('backend.worker.verify', verification)
    monkeypatch.setattr('backend.worker.session_usage', lambda *_: {'available': False})
    return worker, task, tmp_path, verification


def terminal():
    return {'exists': True, 'running': False, 'terminal': True,
            'promptObserved': True, 'userMessages': 1, 'calls': 0}


@pytest.mark.parametrize('state,code', [
    ({'exists': False}, 'ORIGINAL_SESSION_MISSING_NO_REPLAY'),
    ({'exists': True, 'running': False, 'promptObserved': False}, 'PROMPT_ACCEPTANCE_UNKNOWN_NO_REPLAY')])
def test_ambiguous_prompt_never_creates_or_resends(lifecycle, state, code):
    worker, task, run, verify = lifecycle
    worker.rpc_process = Mock(side_effect=[state, {}])
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == ['inspect', 'restore']
    assert worker.service.finish.call_args.args[3] == 'BLOCKED'
    assert worker.service.finish.call_args.kwargs['error_code'] == code
    worker.revoke_local.assert_called_once_with(task)
    verify.assert_not_called()


def test_existing_continuation_intent_is_observed_not_resent(lifecycle):
    worker, task, run, verify = lifecycle
    (run / 'continuation-request.json').write_text('{}')
    worker.rpc_process = Mock(side_effect=[terminal(), terminal(), {}])
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == ['inspect', 'poll', 'restore']
    verify.assert_called_once_with(run, continuation=True)
    assert worker.service.finish.call_args.args[3] == 'SUCCEEDED'


def test_cleanup_failure_is_recorded_without_replaying_success(lifecycle, capsys):
    worker, task, run, verify = lifecycle
    def rpc(mode, *_):
        if mode == 'restore':
            raise RuntimeError('DESKTOP_RESTORE_FAILED')
        return terminal()
    worker.rpc_process = Mock(side_effect=rpc)
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == ['inspect', 'poll', 'poll', 'restore']
    worker.service.finish.assert_called_once()
    assert worker.service.finish.call_args.args[3] == 'SUCCEEDED'
    records = list(run.glob('backend-restore-pending-*.json'))
    assert len(records) == 1
    assert json.loads(records[0].read_text())['error_code'] == 'RESTORE_PENDING_REQUIRES_IDLE_APP'
    assert 'RESTORE_PENDING_REQUIRES_IDLE_APP' in capsys.readouterr().out
    assert not list(run.glob('backend-restored-*.json'))


def test_created_unstarted_session_rebinds_then_sends_once(lifecycle):
    worker, task, run, verify = lifecycle
    (run / 'prompt-request.json').unlink()
    idle = {'exists': True, 'running': False, 'terminal': False, 'userMessages': 0, 'calls': 0}
    worker.rpc_process = Mock(side_effect=[idle, {}, {}, terminal(), {}])
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == ['inspect', 'rebind', 'start-existing', 'poll', 'restore']
    assert worker.service.finish.call_args.args[3] == 'SUCCEEDED'


@pytest.mark.parametrize('field,value', [('exists', False), ('running', True), ('terminal', True),
                                      ('userMessages', 1), ('calls', 1)])
def test_created_session_with_work_cannot_be_treated_as_unstarted(lifecycle, field, value):
    worker, task, run, verify = lifecycle
    (run / 'prompt-request.json').unlink()
    idle = {'exists': True, 'running': False, 'terminal': False, 'userMessages': 0, 'calls': 0}
    idle[field] = value
    worker.rpc_process = Mock(side_effect=[idle, {}])
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == ['inspect', 'restore']
    assert worker.service.finish.call_args.kwargs['error_code'] == 'ORIGINAL_SESSION_NOT_PROVEN_UNSTARTED'


@pytest.mark.parametrize('saved', [(), ('session-created.json',),
                                  ('session-created.json', 'model-selected.json')])
def test_creation_and_selection_response_windows_use_original_session(lifecycle, saved):
    worker, task, run, verify = lifecycle
    (run / 'prompt-request.json').unlink()
    for name in saved:
        (run / name).write_text('{}')
    idle = {'exists': True, 'running': False, 'terminal': False, 'userMessages': 0, 'calls': 0}
    worker.rpc_process = Mock(side_effect=[idle, {}, {}, terminal(), {}])
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == [
        'inspect', 'rebind', 'start-existing', 'poll', 'restore']
    assert worker.service.finish.call_args.args[3] == 'SUCCEEDED'


@pytest.mark.parametrize('response_saved', [False, True])
def test_prompt_response_presence_never_triggers_resend(lifecycle, response_saved):
    worker, task, run, verify = lifecycle
    if response_saved:
        (run / 'prompt-response.json').write_text('{}')
    worker.rpc_process = Mock(side_effect=[terminal(), terminal(), terminal(), {}])
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == [
        'inspect', 'poll', 'poll', 'restore']
    assert worker.service.finish.call_args.args[3] == 'SUCCEEDED'


@pytest.mark.parametrize('failed_mode', ['activate', 'start'])
def test_initial_side_effect_failure_is_not_retried(lifecycle, failed_mode):
    worker, task, run, verify = lifecycle
    for name in ('active-tasks.json', 'create-request.json', 'prompt-request.json'):
        (run / name).unlink()
    def rpc(mode, *_):
        if mode == failed_mode:
            raise RuntimeError('DESKTOP_' + mode.upper() + '_FAILED')
        return {}
    worker.rpc_process = Mock(side_effect=rpc)
    worker.execute(task)
    modes = [c.args[0] for c in worker.rpc_process.call_args_list]
    assert modes == (['activate'] if failed_mode == 'activate' else ['activate', 'start', 'restore'])
    assert worker.service.finish.call_args.args[3] == 'BLOCKED'
    assert worker.service.finish.call_args.kwargs['error_code'] == 'DESKTOP_' + failed_mode.upper() + '_FAILED'
    worker.revoke_local.assert_called_once_with(task)
    verify.assert_not_called()


def test_unknown_continuation_only_observes_and_blocks(lifecycle):
    worker, task, run, verify = lifecycle
    (run / 'continuation-request.json').write_text('{}')
    worker.rpc_process = Mock(side_effect=[terminal(), RuntimeError('DESKTOP_POLL_FAILED'), {}])
    worker.execute(task)
    assert [c.args[0] for c in worker.rpc_process.call_args_list] == ['inspect', 'poll', 'restore']
    assert worker.service.finish.call_args.args[3] == 'BLOCKED'
    worker.revoke_local.assert_called_once_with(task)
    verify.assert_not_called()


def test_partial_preparation_never_activates_or_sends(lifecycle):
    worker, task, run, verify = lifecycle
    worker.prepare_task.side_effect = RuntimeError('PARTIAL_PREPARATION_NEEDS_REVIEW')
    worker.rpc_process = Mock()
    worker.execute(task)
    worker.rpc_process.assert_not_called()
    assert worker.service.finish.call_args.args[3] == 'BLOCKED'
    assert worker.service.finish.call_args.kwargs['error_code'] == 'PARTIAL_PREPARATION_NEEDS_REVIEW'
    worker.revoke_local.assert_called_once_with(task)
