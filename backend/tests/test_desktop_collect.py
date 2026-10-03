import secrets
import sys
from unittest.mock import Mock, patch
import pytest
from backend.desktop_client import DesktopControlClient
from backend.desktop_collect import collect_guest_bundle, run_bounded
import test_desktop_bundle as bundles


def test_real_process_bounded_bidirectional_io():
    payload = b'x' * 32768
    result = run_bounded([sys.executable, '-c', 'import sys; d=sys.stdin.buffer.read(); sys.stdout.buffer.write(d)'], payload)
    assert result == payload


@pytest.mark.parametrize('script,limit,timeout', [
    ('import sys; sys.stdout.buffer.write(b"x"*10000)', 100, 2),
    ('import time; time.sleep(10)', 100, .05),
    ('import sys; sys.exit(2)', 100, 2),
])
def test_real_process_output_timeout_and_exit_fail_closed(script, limit, timeout):
    with pytest.raises(RuntimeError, match='GUEST_COLLECTION_UNCONFIRMED'):
        run_bounded([sys.executable, '-c', script], b'', limit=limit, timeout=timeout)


@pytest.fixture
def collector(tmp_path):
    root = tmp_path / bundles.RUN
    root.mkdir(mode=0o700)
    wrapper = tmp_path / 'vm-ssh'
    wrapper.write_text('#!/bin/sh\nexit 1\n')
    wrapper.chmod(0o700)
    client = DesktopControlClient(port=19001, token=secrets.token_urlsafe(32), run_id=bundles.RUN,
                                  owner=bundles.OWNER, epoch=1)
    client.status = Mock(return_value={'stopped': True, 'pendingCalls': 0, 'rawCalls': 10})
    client.inspect = Mock(return_value={'lease': {'stopped': True}})
    return dict(root=root, ssh_wrapper=wrapper, deployment='/Users/mvpagent/CUAgent-p6-' + 'a' * 40,
                client=client, submission=bundles.SUBMISSION)


def test_collection_uses_fixed_command_and_preserves_original_tar_once(collector):
    files, manifest = bundles.fixture()
    raw = bundles.pack(files, manifest)
    with patch('backend.desktop_collect.run_bounded', return_value=raw) as run:
        result = collect_guest_bundle(**collector)
        assert result['sessionVerified'] is False
        assert result['files'] == files
        args, payload = run.call_args.args
        assert 'desktop_export.py' in args[-1]
        assert '--run ' + bundles.RUN in args[-1]
        assert 'ClearAllForwardings=yes' in args
        assert collector['client'].token not in str(args)
        assert b'lines' in payload
        assert (collector['root'] / 'guest-evidence.tar').read_bytes() == raw
        with pytest.raises(FileExistsError):
            collect_guest_bundle(**collector)
        run.assert_called_once()


def test_pending_guest_or_unapproved_deployment_never_starts_ssh(collector):
    with patch('backend.desktop_collect.run_bounded') as run:
        collector['client'].status.return_value['pendingCalls'] = 1
        with pytest.raises(ValueError): collect_guest_bundle(**collector)
        collector['client'].status.return_value['pendingCalls'] = 0
        collector['deployment'] += ';touch /tmp/no'
        with pytest.raises(ValueError): collect_guest_bundle(**collector)
        run.assert_not_called()


def test_bad_bundle_preserved_but_never_accepted(collector):
    with patch('backend.desktop_collect.run_bounded', return_value=b'bad tar'):
        with pytest.raises(ValueError): collect_guest_bundle(**collector)
    assert (collector['root'] / 'guest-evidence.tar').read_bytes() == b'bad tar'


def test_state_changed_after_collection_is_rejected(collector):
    files, manifest = bundles.fixture()
    collector['client'].status.side_effect = [
        {'stopped': True, 'pendingCalls': 0, 'rawCalls': 10},
        {'stopped': True, 'pendingCalls': 1, 'rawCalls': 11}]
    with patch('backend.desktop_collect.run_bounded', return_value=bundles.pack(files, manifest)):
        with pytest.raises(RuntimeError, match='STATE_CHANGED'): collect_guest_bundle(**collector)
