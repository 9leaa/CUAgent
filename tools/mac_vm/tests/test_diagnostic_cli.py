"""Real local filesystem/socket validation; subprocess/VM identity simulated."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import driver_smoke as driver


@pytest.fixture
def cli(tmp_path,monkeypatch):
    root=tmp_path/'diagnostic';root.mkdir(mode=0o700)
    binary=root/'cua-driver';binary.write_bytes(b'fixture');binary.chmod(0o700)
    short=tempfile.TemporaryDirectory(prefix='cua-',dir='/tmp')
    endpoint=Path(short.name).resolve()/'daemon.sock'
    sock=socket.socket(socket.AF_UNIX);sock.bind(str(endpoint))
    monkeypatch.setattr(driver,'DIAGNOSTIC_DRIVER',str(binary))
    monkeypatch.setattr(driver,'DIAGNOSTIC_SHA256',hashlib.sha256(b'fixture').hexdigest())
    monkeypatch.setattr(driver,'DIAGNOSTIC_SOCKET',str(endpoint))
    monkeypatch.setattr(driver,'require_vm',Mock())
    run=Mock(return_value=SimpleNamespace(returncode=0,stdout='{"ok":true}',stderr=''))
    monkeypatch.setattr(driver.subprocess,'run',run)
    try:yield binary,endpoint,run
    finally:sock.close();short.cleanup()


def test_exact_socket_and_no_fallback(cli):
    binary,endpoint,run=cli
    assert driver.diagnostic_cli('get_window_state',{'session':'original'})=={'ok':True}
    assert run.call_args.args[0]==[str(binary),'--socket',str(endpoint),'get_window_state',json.dumps({'session':'original'})]
    assert run.call_count==1


@pytest.mark.parametrize('mutation',['hash','missing','symlink','hardlink','public','noexecute','publicdir','socketfile','socketlink'])
def test_fail_closed_before_dispatch(cli,mutation):
    binary,endpoint,run=cli
    if mutation=='hash':binary.write_bytes(b'changed')
    elif mutation=='missing':binary.unlink()
    elif mutation=='symlink':
        saved=binary.with_name('saved');binary.rename(saved);binary.symlink_to(saved)
    elif mutation=='hardlink':os.link(binary,binary.with_name('copy'))
    elif mutation=='public':binary.chmod(0o755)
    elif mutation=='noexecute':binary.chmod(0o600)
    elif mutation=='publicdir':binary.parent.chmod(0o755)
    elif mutation=='socketfile':endpoint.unlink();endpoint.write_text('not socket')
    elif mutation=='socketlink':
        saved=endpoint.with_name('saved.sock');endpoint.rename(saved);endpoint.symlink_to(saved)
    with pytest.raises((driver.StopRun,OSError)):driver.diagnostic_cli('click',{})
    run.assert_not_called()


def test_detailed_failure_not_replayed(cli):
    _,_,run=cli
    run.return_value=SimpleNamespace(returncode=1,stdout='{"code":"foreground_unavailable"}',stderr='actual cause')
    with pytest.raises(driver.DriverCallError) as caught:driver.diagnostic_cli('click',{})
    assert caught.value.diagnostic['stderr']['preview']=='actual cause'
    assert run.call_count==1


def test_default_cli_unchanged(cli):
    _,_,run=cli
    driver.Calls.cli('click',{})
    assert run.call_args.args[0]==[driver.DRIVER,'click','{}']
