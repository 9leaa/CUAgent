import json
import io
import shlex
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch
import pytest

from backend.desktop_prepare_cleanup import cleanup_prepared_guest
from backend import desktop_cleanup_protocol as protocol

RUN = 'p2-11111111-1111-1111-1111-111111111111'
OWNER = '22222222-2222-2222-2222-222222222222'


@pytest.fixture
def cleanup(tmp_path):
    root = tmp_path / RUN
    root.mkdir(mode=0o700)
    wrapper = tmp_path / 'ssh'
    wrapper.write_text('#!/bin/sh\nexit 1\n')
    wrapper.chmod(0o700)
    binding = {'version': 1, 'runId': RUN, 'owner': OWNER, 'epoch': 1}
    ready = {'binding': binding, 'pid': 808, 'activated': False, 'controlHost': '127.0.0.1',
             'controlPort': 19001, 'controlToken': 'c' * 43, 'modelToken': 'm' * 43,
             'modelUrl': 'http://192.168.64.3:8766'}
    result = {'binding': binding, 'closed': True, 'stopped': True,
              'active': False, 'rawCalls': 0, 'pendingCalls': 0}
    return dict(root=root, ssh_wrapper=wrapper, ready=ready, owner=OWNER, epoch=1), result


def test_single_bound_cleanup_secrets_only_stdin_and_private_receipt(cleanup):
    args, result = cleanup
    with patch('backend.desktop_prepare_cleanup.run_bounded', return_value=json.dumps(result).encode()) as run:
        assert cleanup_prepared_guest(**args) == result
        argv, payload = run.call_args.args
        assert args['ready']['controlToken'] not in str(argv)
        assert args['ready']['modelToken'] not in str(argv) + payload.decode()
        request = json.loads(payload)
        assert request['port'] == 19001 and request['token'] == 'c' * 43
        command = shlex.split(argv[-1])
        compile(command[2], '<trusted-cleanup-script>', 'exec')
        assert run.call_args.kwargs == {'limit': 4096, 'timeout': 25}
        with pytest.raises(FileExistsError): cleanup_prepared_guest(**args)
        run.assert_called_once()
    for name in ('desktop-prepare-cleanup-intent.json', 'desktop-prepare-cleanup.json'):
        path = args['root'] / name
        assert path.stat().st_mode & 0o777 == 0o600
        assert 'c' * 43 not in path.read_text()


@pytest.mark.parametrize('change', [dict(closed=False), dict(active=True), dict(stopped=False),
    dict(rawCalls=1), dict(pendingCalls=False), dict(binding={}), dict(secret='do-not-save')])
def test_invalid_cleanup_reply_never_confirmed_or_retried(cleanup, change):
    args, result = cleanup
    with patch('backend.desktop_prepare_cleanup.run_bounded', return_value=json.dumps({**result, **change}).encode()) as run:
        with pytest.raises(ValueError): cleanup_prepared_guest(**args)
        with pytest.raises(FileExistsError): cleanup_prepared_guest(**args)
        run.assert_called_once()
    assert not (args['root'] / 'desktop-prepare-cleanup.json').exists()


def test_transport_unknown_never_retried(cleanup):
    args, _ = cleanup
    with patch('backend.desktop_prepare_cleanup.run_bounded', side_effect=RuntimeError('unknown')) as run:
        with pytest.raises(RuntimeError): cleanup_prepared_guest(**args)
        with pytest.raises(FileExistsError): cleanup_prepared_guest(**args)
        run.assert_called_once()
    assert not (args['root'] / 'desktop-prepare-cleanup.json').exists()


def test_unvalidated_bootstrap_never_attempts_cleanup(cleanup):
    args, _ = cleanup
    args['ready']['binding']['epoch'] = 2
    with patch('backend.desktop_prepare_cleanup.run_bounded') as run:
        with pytest.raises(ValueError): cleanup_prepared_guest(**args)
        run.assert_not_called()
    assert not (args['root'] / 'desktop-prepare-cleanup-intent.json').exists()


@pytest.mark.parametrize('payload', [b'x' * 4097, b'null', b'{"extra":"secret"}'])
def test_remote_main_rejects_bad_input_without_constructing_client(payload, capsys):
    from pathlib import Path
    client = Mock()
    with patch.object(protocol.sys, 'platform', 'darwin'), \
            patch.object(protocol.getpass, 'getuser', return_value='mvpagent'), \
            patch.object(protocol.os, 'geteuid', return_value=501), \
            patch.object(protocol.Path, 'home', return_value=Path('/Users/mvpagent')), \
            patch.object(protocol.subprocess, 'check_output', return_value='VirtualMac2,1'), \
            patch.object(protocol.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
        assert protocol.cleanup_main(client) == 1
    client.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == '' and captured.err == 'P6_PREPARE_CLEANUP_UNCONFIRMED\n'
