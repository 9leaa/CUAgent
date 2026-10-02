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


@pytest.mark.parametrize('mode', ['start', 'activate', 'cancel', 'restore'])
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
