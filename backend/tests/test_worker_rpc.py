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
