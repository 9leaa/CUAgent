"""Model adapter on original ledger; simulated Driver, no real DSH execution."""
import copy
from functools import partial
import pytest
import test_calc_input_task as base
from test_calc_targeting import state
from calc_input_model_task import CalcInputModelTask
from test_calc_edit import fixture


@pytest.fixture
def adapter(tmp_path,state,request,monkeypatch):
    _,regions=fixture()
    state['elements'][2]['frame']=dict(x=110,y=60,w=80,h=20)
    monkeypatch.setattr(base,'CalcInputTask',partial(CalcInputModelTask,
        session_id='session-22222222-2222-2222-2222-222222222222',name_box_grid=[0,0,300,80],
        controls_region=regions['controls_region'],editor_regions=regions['editor_regions']))
    yield from base.input_setup.__wrapped__(tmp_path,state,request)


def prepare(task,monkeypatch):
    first=task.observe()
    result=task.select_cell(dict(snapshot_id=first['state']['snapshot_id'],x=90,y=120))
    assert result['protocol']=='calc-input-v1' and not task.stopped.is_set()
    original=task.transport;source,_=fixture();typed=[False]
    def driver(tool,args):
        if tool=='type_text':typed[0]=True
        value=original(tool,args)
        if tool=='get_window_state' and typed[0]:
            for e in source['elements'][1:]:
                e=copy.deepcopy(e);e['element_index']+=10
                e['element_token']=value['snapshot_id']+':'+str(e['element_index'])
                if e['role']=='AXTextArea':e['value']='AbZ中文'
                value['elements'].append(e)
        return value
    monkeypatch.setattr(task,'transport',driver)
    return dict(snapshot_id=result['state']['snapshot_id'],text='AbZ中文',kind='text')


@pytest.mark.parametrize('adapter',[True],indirect=True)
def test_model_selection_input_commit_original_seven_raw(adapter,monkeypatch):
    t,calls,*_=adapter;args=prepare(t,monkeypatch)
    value=t.input_cell(args)
    assert value['status']=='INPUT_OBSERVED' and value['confirmation']['inputEffectVerified']
    assert t.used==5 and not t.stopped.is_set()
    result=t.commit_cell(dict(snapshot_id=value['state']['snapshot_id']))
    assert result['status']=='COMMIT_ATTEMPT_OBSERVED' and t.used==7 and t.stopped.is_set()
    assert result['businessStatus']=='UNVERIFIED' and len(calls)==7


@pytest.mark.parametrize('change',[{'name_box_index':2},{'pid':10},{'text':'other'},{'snapshot_id':'old'}])
def test_model_cannot_replace_scope_or_payload(adapter,monkeypatch,change):
    t,calls,*_=adapter;args=prepare(t,monkeypatch);args.update(change)
    with pytest.raises(Exception):t.input_cell(args)
    assert len(calls)==3 and t.stopped.is_set()


def test_model_cannot_choose_commit_target(adapter,monkeypatch):
    t,calls,*_=adapter;args=prepare(t,monkeypatch);value=t.input_cell(args)
    with pytest.raises(ValueError):t.commit_cell(dict(snapshot_id=value['state']['snapshot_id'],element_index=12))
    assert len(calls)==5 and t.stopped.is_set()


def test_already_selected_requires_second_observation_without_click(adapter):
    t,calls,*_=adapter;t.observe()
    result=t.select_cell(dict(snapshot_id=t.snapshot['snapshot_id']))
    assert result['selectionRoute']=='already-selected' and result['status']=='SELECTION_OBSERVED'
    assert t.used==2 and [tool for tool,_ in calls]==['get_window_state','get_window_state']
    assert t.phase=='CONFIRMED' and not t.stopped.is_set()


def test_driver_confirmed_existing_text_without_edit_state_is_not_input_success(adapter,monkeypatch):
    t,calls,s,*_=adapter
    s['elements'][1]['value']='AbZ中文'
    original=t.transport
    def transport(tool,args):
        result=original(tool,args)
        if tool=='type_text':
            return dict(effect='confirmed',delivery=dict(delivered_count=5,mode='foreground'))
        return result
    monkeypatch.setattr(t,'transport',transport)
    t.observe();t.select_cell(dict(snapshot_id=t.snapshot['snapshot_id']))
    with pytest.raises(ValueError,match='unique enabled edit controls required'):
        t.input_cell(dict(snapshot_id=t.snapshot['snapshot_id'],text='AbZ中文',kind='text'))
    assert t.used==4 and t.stopped.is_set()
    assert [tool for tool,_ in calls]==['get_window_state','get_window_state','type_text','get_window_state']
    with pytest.raises(Exception):t.commit_cell(dict(snapshot_id=t.snapshot['snapshot_id']))
    assert t.used==4 and len(calls)==4


def test_approved_pending_edit_precedes_already_selected(adapter):
    t,calls,*_=adapter
    source,regions=fixture()
    t.edit_cancel=dict(approved=True,expected_text='AbZ中文',
        controls_region=regions['controls_region'],editor_regions=regions['editor_regions'])
    t.observe()
    for element in source['elements'][1:]:
        e=copy.deepcopy(element);e['element_index']+=10
        e['element_token']=t.snapshot['snapshot_id']+':'+str(e['element_index'])
        if e['role']=='AXTextArea':e['value']='AbZ中文'
        t.snapshot['elements'].append(e)
    result=t.select_cell(dict(snapshot_id=t.snapshot['snapshot_id']))
    assert result['status']=='NEEDS_EDIT_CANCEL'
    assert t.phase=='NEW' and t.used==1 and len(calls)==1
    assert not t._edit_cancel_attempted


def test_no_implicit_edit_cancel_authority(adapter):
    t,calls,*_=adapter;t.observe()
    with pytest.raises(ValueError):
        t.select_cell(dict(snapshot_id=t.snapshot['snapshot_id'],cancel_edit=True))
    assert t.used==1 and len(calls)==1


@pytest.mark.parametrize('fault',['changed','same','lease','budget','stopped'])
def test_current_selection_recheck_never_falls_back_to_click(adapter,monkeypatch,fault):
    t,calls,s,control,lease,*_=adapter;t.observe();snapshot=t.snapshot['snapshot_id']
    original=t.transport
    def transport(tool,args):
        result=original(tool,args)
        if fault=='changed':result['elements'][2]['value']='B2'
        if fault=='same':result['snapshot_id']=snapshot
        return result
    monkeypatch.setattr(t,'transport',transport)
    if fault=='lease':
        import json
        control.write_text(json.dumps(dict(lease,stopped=True)))
    if fault=='budget':t.used=30
    if fault=='stopped':t.stop()
    with pytest.raises(Exception):t.select_cell(dict(snapshot_id=snapshot))
    assert all(tool=='get_window_state' for tool,_ in calls)


def test_not_selected_uses_original_screenshot_fallback(adapter):
    t,calls,s,*_=adapter;s['elements'][2]['value']='B2';t.observe()
    result=t.select_cell(dict(snapshot_id=t.snapshot['snapshot_id']))
    assert result['status']=='NEEDS_SCREENSHOT_POINT' and t.used==1 and len(calls)==1
