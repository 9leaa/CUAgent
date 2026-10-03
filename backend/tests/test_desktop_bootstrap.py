import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
from unittest.mock import Mock, patch
import pytest
from backend.desktop_bootstrap import bootstrap_guest

spec = importlib.util.spec_from_file_location('guest_bootstrap_test', Path(__file__).resolve().parents[2] / 'tools/mac_vm/desktop_bootstrap.py')
guest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guest)
COMMIT = 'a' * 40
RUN = 'p2-11111111-1111-1111-1111-111111111111'
OWNER = '22222222-2222-2222-2222-222222222222'


def receipt():
    return {'binding': {'version': 1, 'runId': RUN, 'owner': OWNER, 'epoch': 1}, 'pid': 808,
            'controlHost': '127.0.0.1', 'controlPort': 19001, 'modelUrl': 'http://192.168.64.3:8766',
            'activated': False, 'modelToken': secrets.token_urlsafe(32), 'controlToken': secrets.token_urlsafe(32)}


@pytest.fixture
def deployment(tmp_path):
    directory = tmp_path / ('CUAgent-p6-' + COMMIT)
    directory.mkdir(mode=0o700)
    source = b'# synthetic, never executed\n'
    (directory / 'desktop_guest.py').write_bytes(source)
    (directory / 'desktop_guest.py').chmod(0o600)
    manifest = json.dumps({'commit': COMMIT, 'files': {'desktop_guest.py': hashlib.sha256(source).hexdigest()}}).encode()
    (directory / 'deployment-manifest.json').write_bytes(manifest)
    (directory / 'deployment-manifest.json').chmod(0o600)
    return tmp_path, dict(commit=COMMIT, manifest_sha=hashlib.sha256(manifest).hexdigest(), run_id=RUN, owner=OWNER, epoch=1)


def test_guest_launch_checks_hash_and_returns_own_private_receipt(deployment):
    home, kwargs = deployment
    ready = receipt()
    process = Mock(pid=808)
    process.poll.return_value = None
    def launch(*args, **options):
        run = home / 'C0Evidence' / RUN
        run.mkdir(mode=0o700, parents=True)
        for name, data in [('guest-ready.json', json.dumps({k: v for k, v in ready.items() if not k.endswith('Token')})),
                           ('bridge-token', ready['modelToken']), ('control-token', ready['controlToken'])]:
            (run / name).write_text(data)
            (run / name).chmod(0o600)
        return process
    with patch.object(guest.subprocess, 'Popen', side_effect=launch) as popen:
        assert guest.bootstrap(home, **kwargs) == ready
        popen.assert_called_once()
        assert '--approve-task' in popen.call_args.args[0]
        with pytest.raises(ValueError): guest.bootstrap(home, **kwargs)


def test_source_change_prevents_launch(deployment):
    home, kwargs = deployment
    (home / ('CUAgent-p6-' + COMMIT) / 'desktop_guest.py').write_text('changed')
    with patch.object(guest.subprocess, 'Popen') as popen:
        with pytest.raises(ValueError): guest.bootstrap(home, **kwargs)
        popen.assert_not_called()
    assert not (home / 'P6Launch').exists()


def test_unknown_ready_does_not_restart_or_kill_guest(deployment):
    home, kwargs = deployment
    process = Mock(pid=808)
    process.poll.return_value = None
    with patch.object(guest.subprocess, 'Popen', return_value=process) as popen, \
            patch.object(guest.time, 'monotonic', side_effect=[0, 11]):
        with pytest.raises(ValueError): guest.bootstrap(home, **kwargs)
        popen.assert_called_once()
        process.kill.assert_not_called()
        process.terminate.assert_not_called()


@pytest.fixture
def host(tmp_path):
    root = tmp_path / RUN
    root.mkdir(mode=0o700)
    wrapper = tmp_path / 'ssh'
    wrapper.write_text('#!/bin/sh\nexit 1\n')
    wrapper.chmod(0o700)
    return dict(root=root, ssh_wrapper=wrapper, commit=COMMIT, manifest_sha='b' * 64, owner=OWNER, epoch=1)


def test_host_saves_private_receipt_once(host):
    ready = receipt()
    with patch('backend.desktop_bootstrap.run_bounded', return_value=json.dumps(ready).encode()) as run:
        assert bootstrap_guest(**host) == ready
        path = host['root'] / 'guest-private-receipt.json'
        assert path.stat().st_mode & 0o077 == 0
        assert ready['controlToken'] not in str(run.call_args.args)
        with pytest.raises(FileExistsError): bootstrap_guest(**host)
        run.assert_called_once()


@pytest.mark.parametrize('change', [{'pid': True}, {'controlPort': 0}, {'activated': True}, {'binding': {}}, {'modelToken': 'bad'}])
def test_wrong_ready_fails_without_replay(host, change):
    with patch('backend.desktop_bootstrap.run_bounded', return_value=json.dumps({**receipt(), **change}).encode()) as run:
        with pytest.raises(ValueError): bootstrap_guest(**host)
        with pytest.raises(FileExistsError): bootstrap_guest(**host)
        run.assert_called_once()
