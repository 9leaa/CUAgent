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
