"""Launcher lifecycle tests: no model, VM or GUI actions."""
from unittest.mock import Mock
from pathlib import Path
import sys
import threading
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calc_model_guest import credential, serve, main


@pytest.mark.parametrize('ending', ['deadline', 'signal', 'stopped', 'lease', 'http'])
def test_termination_always_stops_revokes_drains_then_closes(ending):
    events = []
    task = Mock()
    task.stopped = threading.Event()
    task.stop.side_effect = lambda: events.append('stop')
    task.close.side_effect = lambda: events.append('close')
    server = Mock()
    server.server_close.side_effect = lambda: events.append('drain')
    controller = Mock()
    controller.revoke.side_effect = lambda: events.append('revoke')
    stopping = threading.Event()
    if ending == 'signal': stopping.set()
    if ending == 'stopped': task.stopped.set()
    if ending == 'lease': controller.gate.check.side_effect = ValueError('expired')
    if ending == 'http': server.handle_request.side_effect = ValueError('transport')
    ticks = iter([0, 181] if ending == 'deadline' else [0, 1])
    if ending in ('lease', 'http'):
        with pytest.raises(ValueError): serve(task, server, controller, stopping, clock=lambda: next(ticks))
    else:
        serve(task, server, controller, stopping, clock=lambda: next(ticks))
    assert events == ['stop', 'revoke', 'drain', 'close']
    assert server.daemon_threads is False and server.block_on_close is True
    task.observe.assert_not_called()
    controller.renew.assert_not_called()


def test_revocation_error_does_not_skip_cleanup():
    task, server, controller = Mock(), Mock(), Mock()
    task.stopped.is_set.return_value = True
    controller.revoke.side_effect = OSError('disk')
    with pytest.raises(OSError): serve(task, server, controller, threading.Event())
    server.server_close.assert_called_once()
    task.close.assert_called_once()


@pytest.mark.parametrize('fault', ['public', 'symlink', 'hardlink', 'oversize', 'invalid', 'valid'])
def test_private_credentials(tmp_path, fault):
    path = tmp_path/'token'
    path.write_text('x'*43)
    path.chmod(0o600)
    if fault == 'public': path.chmod(0o644)
    if fault == 'symlink':
        link = tmp_path/'link'; link.symlink_to(path); path = link
    if fault == 'hardlink': (tmp_path/'link').hardlink_to(path)
    if fault == 'oversize': path.write_text('x'*129)
    if fault == 'invalid': path.write_text('x'*43+'\n')
    if fault == 'valid': assert credential(path) == 'x'*43
    else:
        with pytest.raises((OSError, ValueError)): credential(path)


def test_no_approval_never_checks_vm(monkeypatch):
    check = Mock()
    monkeypatch.setattr('calc_model_guest.require_unlocked', check)
    with pytest.raises(SystemExit): main([])
    check.assert_not_called()


@pytest.mark.parametrize('extra',[
    ['--approve-cancel-edit'],['--pending-edit-text','a'],
    ['--edit-controls-region','1','2','3','4'],
    ['--approve-cancel-edit','--pending-edit-text','a'],
])
def test_partial_edit_approval_rejected_before_vm(monkeypatch,extra):
    check=Mock();monkeypatch.setattr('calc_model_guest.require_unlocked',check)
    args=['--run','calc-select-11111111-1111-1111-1111-111111111111',
          '--owner','22222222-2222-2222-2222-222222222222',
          '--session','session-33333333-3333-3333-3333-333333333333',
          '--epoch','1','--pid','10','--window','20','--title','probe','--cell','A1',
          '--grid','0','80','700','550','--name-box-grid','0','0','300','80','--approve-selection']
    with pytest.raises(SystemExit):main(args+extra)
    check.assert_not_called()


@pytest.mark.parametrize('failure', [None, 'factory', 'listener'])
def test_main_original_binding_and_failed_start_never_replays(tmp_path, monkeypatch, failure):
    import json
    import time
    from desktop_control import LeaseController
    run = 'calc-select-11111111-1111-1111-1111-111111111111'
    owner = '22222222-2222-2222-2222-222222222222'
    session = 'session-33333333-3333-3333-3333-333333333333'
    directory = tmp_path/run
    directory.mkdir(mode=0o700)
    controller = LeaseController(directory/'lease.json', run_id=run, owner=owner, epoch=1, clock=time.time)
    controller.renew(1)
    for name, token in [('bridge-token','x'*43), ('control-token','y'*43)]:
        path = directory/name; path.write_text(token); path.chmod(0o600)
    monkeypatch.setattr('calc_model_guest.SHARED_LOCK', tmp_path/'bridge.lock')
    monkeypatch.setattr('calc_model_guest.require_unlocked', lambda: None)
    task = Mock()
    task.stopped.is_set.return_value = True
    factory = Mock(return_value=task)
    server = Mock()
    listener = Mock(return_value=server)
    if failure == 'factory': factory.side_effect = ValueError('factory')
    if failure == 'listener': listener.side_effect = ValueError('listener')
    monkeypatch.setattr('calc_model_guest.CalcModelTask', factory)
    monkeypatch.setattr('calc_model_guest.tools_server', listener)
    args = ['--run',run,'--owner',owner,'--session',session,'--epoch','1','--pid','10',
            '--window','20','--title','probe','--cell','A1','--grid','0','80','700','550',
            '--name-box-grid','0','0','300','80','--approve-selection']
    if failure:
        with pytest.raises(ValueError): main(args)
    else:
        assert main(args) == 0
        ready = json.loads((directory/'calc-ready.json').read_text())
        assert ready['sessionId'] == session and ready['inputPermitted'] is False
        assert 'token' not in (directory/'calc-ready.json').read_text()
    assert controller.existing()['stopped'] is True
    intent = (directory/'calc-start-intent.json').read_bytes()
    assert json.loads(intent)['sessionId'] == session
    from driver_smoke import StopRun
    with pytest.raises(StopRun): main(args)
    assert (directory/'calc-start-intent.json').read_bytes() == intent
    factory.assert_called_once()
    task.observe.assert_not_called()
