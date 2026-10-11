"""Original persisted ledger with simulated Driver; no real GUI success claim."""
import base64
import copy
import json
from pathlib import Path
import struct
import sys
import threading
import zlib
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calc_input_task import CalcInputTask
from desktop_lease import LeaseGate
from driver_smoke import StopRun
from test_calc_targeting import state


@pytest.fixture
def input_setup(tmp_path,state):
    tmp_path.chmod(0o700)
    control=tmp_path/'lease.json'
    lease=dict(version=1,runId='input',owner='worker',epoch=1,stopped=False,expiresAt=120000)
    control.write_text(json.dumps(lease));control.chmod(0o600)
    calls=[];serial=[0];fault=[None]
    def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',800,600,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'*(801*600)))+chunk(b'IEND',b'')
    state['screenshot_png_b64']=base64.b64encode(png).decode();state['elements_complete']=False
    def transport(tool,args):
        calls.append((tool,copy.deepcopy(args)))
        if tool=='type_text' and fault[0]=='timeout':raise TimeoutError('simulated unknown input')
        if tool=='type_text' and fault[0]=='refused':return {'effect':'refused'}
        if tool=='get_window_state':
            if fault[0]=='post_error' and any(t=='type_text' for t,_ in calls):raise RuntimeError('missing new observation')
            serial[0]+=1;s=copy.deepcopy(state);s['snapshot_id']=f's{serial[0]:08x}'
            for e in s['elements']:e['element_token']=s['snapshot_id']+':'+str(e['element_index'])
            return s
        return {'effect':'unverifiable'}
    def factory(**updates):
        options=dict(input_approved=True,overwrite_disposable=True,approved_text='AbZ中文',approved_kind='text')
        options.update(updates)
        return CalcInputTask(tmp_path/'input',lease=LeaseGate(control,run_id='input',owner='worker',epoch=1,clock=lambda:100),
            pid=10,window_id=20,title='probe',cell='A1',grid=[0,80,700,550],approved=True,
            transport=transport,identity=lambda pid:None,environment=lambda:None,shared_lock=tmp_path/'bridge.lock',**options)
    task=factory()
    yield task,calls,state,control,lease,factory,fault
    task.close()


def selected(task):
    task.observe();task.select(point=dict(snapshot_id=task.snapshot['snapshot_id'],x=90,y=120))
    task.confirm(name_box_index=2)


def write(task,**changes):
    args=dict(snapshot_id=task.snapshot['snapshot_id'] if task.snapshot else '',name_box_index=2,text='AbZ中文',kind='text')
    args.update(changes)
    return task.input_once(**args)


def test_one_input_new_observation_original_budget(input_setup):
    t,calls,*_=input_setup;selected(t);result=write(t)
    assert [x[0] for x in calls]==['get_window_state','click','get_window_state','type_text','get_window_state']
    assert calls[3][1]==dict(pid=10,window_id=20,session='input',element_token='s00000002:1',text='AbZ中文',delivery_mode='foreground')
    assert t.used==5 and result['status']=='INPUT_ATTEMPT_OBSERVED'
    assert not result['inputEffectVerified'] and not result['commitPermitted']
    assert result['businessStatus']=='UNVERIFIED'
    with pytest.raises(StopRun):write(t)
    assert t.used==5 and len(calls)==5 and t.stopped.is_set()


@pytest.mark.parametrize('fault',['no_selection','stopped','unknown','old','text','kind','wrong_box','lease','budget'])
def test_input_guard_no_dispatch(input_setup,fault):
    t,calls,s,control,lease,*_=input_setup
    if fault!='no_selection':selected(t)
    args={}
    if fault=='stopped':t.stop()
    elif fault=='unknown':t.uncertain=True
    elif fault=='old':args['snapshot_id']='old'
    elif fault=='text':args['text']='abz中文'
    elif fault=='kind':args['kind']='decimal'
    elif fault=='wrong_box':args['name_box_index']=1
    elif fault=='lease':control.write_text(json.dumps(dict(lease,stopped=True)))
    elif fault=='budget':
        for _ in range(26):t.observe()
    before=len(calls)
    with pytest.raises((StopRun,ValueError)):write(t,**args)
    assert len(calls)==before and t.stopped.is_set()


@pytest.mark.parametrize('fault',['timeout','refused','post_error'])
def test_failed_effect_never_retried(input_setup,fault):
    t,calls,*rest=input_setup;selected(t);rest[-1][0]=fault
    with pytest.raises((TimeoutError,StopRun,RuntimeError)):write(t)
    assert t.stopped.is_set() and sum(tool=='type_text' for tool,_ in calls)==1
    if fault=='timeout':assert t.uncertain
    before=len(calls)
    with pytest.raises(StopRun):write(t)
    assert len(calls)==before


def test_reopen_keeps_budget_and_stopped(input_setup):
    t,calls,s,control,lease,factory,_=input_setup;selected(t);write(t);t.close()
    other=factory()
    try:
        assert other.used==5 and other.stopped.is_set()
        with pytest.raises(StopRun):write(other)
        assert len(calls)==5
    finally:other.close()


def test_raw_input_and_inherited_business_methods_stay_closed(input_setup):
    t,calls,*_=input_setup
    with pytest.raises(StopRun):t.raw('type_text',dict(pid=10,window_id=20,text='bad'))
    with pytest.raises(StopRun):t.type_text({})
    assert not calls


@pytest.mark.parametrize('changes',[
    {'input_approved':False}, {'overwrite_disposable':False},
    {'approved_text':'different'}, {'approved_kind':'decimal'},
])
def test_original_approval_binding_cannot_change(input_setup,changes):
    t,calls,s,control,lease,factory,_=input_setup;t.close()
    with pytest.raises(ValueError):factory(**changes)
    assert not calls


def test_failed_intent_audit_prevents_input(input_setup,monkeypatch):
    t,calls,*_=input_setup;selected(t);record=t.record
    def fail_intent(row):
        if row.get('event')=='input_intent':raise OSError('audit unavailable')
        return record(row)
    monkeypatch.setattr(t,'record',fail_intent)
    with pytest.raises(OSError):write(t)
    assert t.stopped.is_set() and t.used==3 and len(calls)==3
    assert (t.directory/'input-attempt.json').exists()


def test_stop_during_input_prevents_followup_observation(input_setup,monkeypatch):
    t,calls,*_=input_setup;selected(t)
    entered=threading.Event();release=threading.Event();errors=[]
    original=t.transport
    def blocking(tool,args):
        if tool=='type_text':
            entered.set()
            assert release.wait(3)
        return original(tool,args)
    monkeypatch.setattr(t,'transport',blocking)
    def run():
        try:write(t)
        except Exception as error:errors.append(error)
    worker=threading.Thread(target=run);worker.start()
    try:
        assert entered.wait(3)
        t.stop()
        with pytest.raises(StopRun):t.close()
        assert t.lock_fd is not None
    finally:
        release.set();worker.join(3)
    assert not worker.is_alive() and len(errors)==1 and isinstance(errors[0],StopRun)
    assert t.used==4 and [tool for tool,_ in calls][-1]=='type_text'
    assert len(calls)==4 and t.stopped.is_set()
