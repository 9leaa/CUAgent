"""Original Task ledger plus simulated Driver. No real GUI/model calls."""
import base64
import copy
import json
from pathlib import Path
import sys
import threading
import struct
import zlib

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calc_selection import CalcSelectionTask
from desktop_lease import LeaseGate
from driver_smoke import StopRun
from test_calc_targeting import state


@pytest.fixture
def setup(tmp_path, state):
    root = tmp_path.resolve()
    root.chmod(0o700)
    control = root / 'lease.json'
    value = dict(version=1,runId='selection',owner='worker',epoch=1,stopped=False,expiresAt=120000)
    control.write_text(json.dumps(value)); control.chmod(0o600)
    calls = []
    serial = [0]
    state['elements_complete'] = False
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    png = (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',800,600,8,0,0,0,0))
           +chunk(b'IDAT',zlib.compress(b'\0'*(801*600)))+chunk(b'IEND',b''))
    state['screenshot_png_b64'] = base64.b64encode(png).decode()
    def transport(tool,args):
        calls.append((tool,copy.deepcopy(args)))
        if tool == 'get_window_state':
            serial[0] += 1
            return copy.deepcopy(state) | dict(snapshot_id='s'+str(serial[0]))
        return dict(ok=True)
    def factory():
        return CalcSelectionTask(root/'selection',lease=LeaseGate(control,run_id='selection',owner='worker',epoch=1,clock=lambda:100),
             pid=10,window_id=20,title='probe',cell='A1',grid=(0,80,700,550),approved=True,
             transport=transport,identity=lambda _:None,environment=lambda:None,shared_lock=root/'bridge.lock')
    task = factory()
    yield task,calls,state,control,value,factory
    task.close()


def point(task):
    return dict(snapshot_id=task.snapshot['snapshot_id'],x=90,y=120)


def test_screenshot_click_observe_confirm_original_ledger(setup):
    task,calls,*_ = setup
    task.observe()
    assert task.select()['status'] == 'NEEDS_SCREENSHOT_POINT'
    assert task.used == 1
    result = task.select(point=point(task))
    assert result['status'] == 'SELECTION_CONFIRMATION_REQUIRED'
    assert [tool for tool,_ in calls] == ['get_window_state','click','get_window_state']
    assert calls[1][1] == dict(pid=10,window_id=20,session='selection',x=90,y=120)
    assert task.confirm(name_box_index=2)['status'] == 'SELECTION_OBSERVED'
    assert task.used == 3
    with pytest.raises(StopRun): task.select(point=point(task))
    rows = [json.loads(line) for line in task.ledger.read_text().splitlines()]
    assert [r['used'] for r in rows if r['event']=='dispatch'] == [1,2,3]
    assert len(list(task.directory.glob('state-*.png'))) == 2
    assert not (task.directory/'result.txt').exists()


def test_unique_ax_same_executor(setup):
    task,calls,state,*_ = setup
    state['elements_complete'] = True
    task.observe(); task.select(); task.confirm(name_box_index=2)
    assert calls[1][1]['element_index'] == 1 and 'x' not in calls[1][1]


@pytest.mark.parametrize('fault',['png','dimensions','audit'])
def test_bad_evidence_stops_without_click(setup,fault):
    task,calls,state,*_ = setup
    if fault=='png': state['screenshot_png_b64']=base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
    elif fault=='dimensions':
        state['screenshot_width']=802;state['window_bounds']['width']=401
    elif fault=='audit': (task.directory/'state-01.json').write_text('preserved')
    with pytest.raises((ValueError,FileExistsError)): task.observe()
    assert task.stopped.is_set() and task.used==1
    assert len(calls)==1
    if fault=='audit': assert (task.directory/'state-01.json').read_text()=='preserved'


@pytest.mark.parametrize('op', ['click','type_text','scroll','write_result','read_result','verify'])
def test_business_tools_not_inherited(setup,op):
    task,calls,*_ = setup
    with pytest.raises(StopRun): getattr(task,op)()
    assert not calls and task.used == 0


def test_raw_passthrough_and_direct_admission_denied(setup):
    task,calls,*_ = setup
    with pytest.raises(StopRun): task.raw('click',dict(pid=10,window_id=20,x=90,y=120))
    with pytest.raises(StopRun): task.admit('get_window_state')
    assert not calls


def test_stopped_before_click(setup):
    task,calls,*_ = setup
    task.observe(); target=point(task); task.stop()
    with pytest.raises(StopRun): task.select(point=target)
    assert len(calls) == 1


def test_lease_loss_during_click_blocks_post_observation(setup):
    task,calls,state,control,value,*_ = setup
    task.observe()
    old = task.transport
    def revoked(tool,args):
        result=old(tool,args)
        if tool=='click': control.write_text(json.dumps(value | dict(stopped=True)))
        return result
    task.transport=revoked
    with pytest.raises(StopRun): task.select(point=point(task))
    assert [tool for tool,_ in calls] == ['get_window_state','click']
    assert task.stopped.is_set() and task.used == 2


def test_unknown_click_never_retries_or_switches_routes(setup):
    task,calls,*_ = setup
    task.observe(); target=point(task)
    def timeout(tool,args):
        calls.append((tool,args)); raise TimeoutError('simulated')
    task.transport=timeout
    with pytest.raises(TimeoutError): task.select(point=target)
    assert task.uncertain
    with pytest.raises(StopRun): task.select(point=target)
    assert len(calls)==2 and task.used==2


def test_wrong_postclick_selection_stops(setup):
    task,calls,state,*_ = setup
    task.observe(); target=point(task)
    state['elements'][2]['value']='B1'
    task.select(point=target)
    with pytest.raises(ValueError): task.confirm(name_box_index=2)
    assert task.stopped.is_set() and task.used==3


def test_budget_reserves_reobservation_and_restart_preserves_count(setup):
    task,calls,state,control,value,factory = setup
    for _ in range(29): task.observe()
    with pytest.raises(StopRun): task.select(point=point(task))
    assert len(calls)==29
    task.close()
    restarted=factory()
    try:
        assert restarted.used==29 and restarted.stopped.is_set()
        with pytest.raises(StopRun): restarted.observe()
    finally: restarted.close()


def test_shared_lock_prevents_second_executor(setup):
    *_,factory=setup
    with pytest.raises(BlockingIOError): factory()


def test_stop_during_click_does_not_wait_or_dispatch_followup(setup):
    task,calls,*_ = setup
    task.observe(); target=point(task)
    entered,release=threading.Event(),threading.Event()
    old=task.transport
    def held(tool,args):
        if tool=='click': entered.set(); assert release.wait(3)
        return old(tool,args)
    task.transport=held
    errors=[]
    def select():
        try: task.select(point=target)
        except Exception as e: errors.append(e)
    worker=threading.Thread(target=select);worker.start()
    try:
        assert entered.wait(2)
        task.stop()
        with pytest.raises(StopRun): task.close()
        assert task.lock_fd is not None
    finally: release.set();worker.join(3)
    assert not worker.is_alive() and errors
    assert [tool for tool,_ in calls]==['get_window_state','click']
