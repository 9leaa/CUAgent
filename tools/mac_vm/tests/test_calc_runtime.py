"""Actual loopback control/client and lease files; simulated GUI transport."""
from pathlib import Path
import sys
import threading
import time
from unittest.mock import Mock
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_calc_model_http import model_setup, state
from calc_runtime import CalcGuestRuntime
from desktop_control import LeaseController
from desktop_control_http import control_server
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed


@pytest.fixture
def runtime(model_setup):
    task,*_ = model_setup
    controller=LeaseController(task.directory/'lease.json',run_id=task.run_id,
                               owner='owner',epoch=1,clock=time.time)
    task.lease=controller.gate
    factory=Mock(return_value=task)
    value=CalcGuestRuntime(task.directory,controller,model_token='m'*43,control_token='c'*43,
        selection=dict(pid=10,window_id=20,title='probe',cell='A1',grid=[0,80,700,550],
                       session_id=task.session_id,name_box_grid=[0,0,300,80]),
        port=0,loopback_test=True,task_factory=factory)
    server=control_server(controller,'c'*43,runtime=value)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01})
    thread.start()
    client=DesktopControlClient(port=server.server_port,token='c'*43,run_id=task.run_id,owner='owner',epoch=1)
    try: yield value,client,factory,task
    finally:
        value.close();server.shutdown();server.server_close();thread.join(3)


def test_host_owned_renew_activate_stop_shutdown(runtime):
    value,client,factory,task=runtime
    assert client.inspect()['lease'] is None
    assert client.status()['active'] is False
    factory.assert_not_called()
    first=client.renew(1,lambda:time.monotonic()+10)
    assert not first['stopped']
    assert client.activate(lambda:time.monotonic()+10)['active']
    factory.assert_called_once()
    assert task.used==0
    assert client.renew(2,lambda:time.monotonic()+10)['sequence']==2
    assert client.revoke()['stopped']
    assert client.status()['stopped']
    assert task.stopped.is_set()
    client.shutdown()
    assert value.closed and task.lock_fd is None


def test_no_lease_or_replay_activation(runtime):
    value,client,factory,task=runtime
    with pytest.raises(ControlUnconfirmed): client.request('POST','/activate',{})
    factory.assert_not_called()
    assert client.inspect()['lease']['stopped']
    with pytest.raises(ControlUnconfirmed): client.renew(1,lambda:time.monotonic()+10)
    with pytest.raises(ControlUnconfirmed): client.request('POST','/activate',{})
    assert (value.directory/'calc-activation-intent.json').exists()


@pytest.mark.parametrize('path',['/activate-handoff','/handoff-input','/cleanup-app'])
def test_old_workflows_never_activate_calc(runtime,path):
    value,client,factory,task=runtime
    with pytest.raises(ControlUnconfirmed): client.request('POST',path,{})
    factory.assert_not_called()
    assert client.inspect()['lease'] is None
    assert task.used==0


def test_stop_does_not_wait_for_model_task_lock(runtime):
    value,client,factory,task=runtime
    client.renew(1,lambda:time.monotonic()+10)
    client.activate(lambda:time.monotonic()+10)
    held=threading.Event();release=threading.Event()
    def hold():
        with task.lock:
            held.set();release.wait(3)
    thread=threading.Thread(target=hold);thread.start();held.wait(1)
    try:
        assert client.revoke()['stopped']
        assert not release.is_set()
    finally: release.set();thread.join(3)


def test_bad_tokens_and_test_injection_are_rejected(runtime):
    value,_,factory,_=runtime
    for extra in (dict(control_token='m'*43),dict(loopback_test=False)):
        args=dict(model_token='m'*43,control_token='c'*43,selection=value.selection,
                  loopback_test=True,task_factory=factory)
        args.update(extra)
        with pytest.raises(ValueError): CalcGuestRuntime(value.directory,value.controller,**args)


@pytest.mark.parametrize('failure',[False,True])
def test_controlled_launcher_has_no_initial_grant_and_closes(runtime,monkeypatch,failure):
    from calc_model_guest import controlled
    value,client,factory,task=runtime
    args=SimpleNamespace(run=task.run_id,session=task.session_id,pid=10,window=20,
                         title='probe',cell='A1',grid=[0,80,700,550],name_box_grid=[0,0,300,80])
    monkeypatch.setattr('calc_model_guest.CalcGuestRuntime',lambda *a,**kw:value)
    server=Mock(server_port=12345)
    def request():
        assert value.controller.existing() is None
        factory.assert_not_called()
        if failure: raise OSError('control failed')
        value.close()
    server.handle_request.side_effect=request
    monkeypatch.setattr('calc_model_guest.control_server',lambda *a,**kw:server)
    if failure:
        with pytest.raises(OSError): controlled(value.directory,value.controller,'m'*43,'c'*43,args)
    else:
        assert controlled(value.directory,value.controller,'m'*43,'c'*43,args)==0
    assert value.closed and value.controller.existing()['stopped']
    factory.assert_not_called()
    server.server_close.assert_called_once()
    with pytest.raises(ValueError): controlled(value.directory,value.controller,'m'*43,'c'*43,args)
