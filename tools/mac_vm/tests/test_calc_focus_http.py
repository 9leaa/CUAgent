"""Authenticated HTTP focus/input on real ledger, simulated Driver only."""
import copy
from functools import partial
import pytest
import test_calc_input_task as base
from test_calc_targeting import state
from test_calc_edit import fixture
from test_calc_model_http import service as original_service, SESSION
from calc_input_model_task import CalcInputModelTask


@pytest.fixture
def adapter(tmp_path,state,request,monkeypatch):
    _,r=fixture()
    state['elements'][2]['frame']=dict(x=110,y=60,w=80,h=20)
    state['elements'].append(dict(element_index=20,parent_index=0,role='AXTextArea',enabled=True,
        value='a',frame=dict(x=300,y=65,w=10,h=12)))
    monkeypatch.setattr(base,'CalcInputTask',partial(CalcInputModelTask,session_id=SESSION,
        name_box_grid=[0,0,300,80],formula_region=[350,20,700,70],
        controls_region=r['controls_region'],editor_regions=[r['editor_regions'][0],[350,20,700,70]]))
    yield from base.input_setup.__wrapped__(tmp_path,state,request)


@pytest.fixture
def service(adapter):
    yield from original_service.__wrapped__(adapter)


def selected(service):
    code,value=service('observe');assert code==200
    code,value=service('select_cell',dict(snapshot_id=value['state']['snapshot_id']));assert code==200
    return dict(snapshot_id=value['state']['snapshot_id'],x=410,y=40)


def test_focus_then_input_real_http(adapter,service,monkeypatch):
    t,calls,*_=adapter;args=selected(service)
    original=t.transport;source,_=fixture();focused=[False];typed=[False]
    def driver(tool,payload):
        if tool=='click':focused[0]=True
        if tool=='type_text':typed[0]=True
        result=original(tool,payload)
        if tool=='get_window_state' and focused[0]:
            result['elements']=[e for e in result['elements'] if e['element_index']!=20]
            for item in source['elements'][1:]:
                e=copy.deepcopy(item);e['element_index']+=10
                if e['element_index']==14:e['frame']['y']=65
                if typed[0] and e['role']=='AXTextArea':e['value']='AbZ中文'
                e['element_token']=result['snapshot_id']+':'+str(e['element_index'])
                result['elements'].append(e)
        return result
    monkeypatch.setattr(t,'transport',driver)
    code,value=service('focus_input',args)
    assert code==200 and value['status']=='INPUT_FOCUS_OBSERVED' and value['used']==4
    assert value['confirmation']['inputEffectVerified'] is False
    assert value['confirmation']['commitPermitted'] is False
    assert value['confirmation']['snapshot_id']==value['state']['snapshot_id']
    code,value=service('input_cell',dict(snapshot_id=value['state']['snapshot_id'],text='AbZ中文',kind='text'))
    assert code==200 and value['status']=='INPUT_OBSERVED' and value['used']==6
    assert [tool for tool,_ in calls]==['get_window_state','get_window_state','click','get_window_state','type_text','get_window_state']
    assert service('focus_input',args)[0]==409 and len(calls)==6 and t.stopped.is_set()


@pytest.mark.parametrize('fault',['session','run','region','text','proof','stale','nan','missing','phase'])
def test_focus_http_cannot_expand_scope(adapter,service,fault):
    t,calls,*_=adapter;args=selected(service);changes={}
    if fault=='session':changes['sessionId']='other'
    if fault=='run':changes['runId']='other'
    if fault=='region':args['editor_regions']=[[0,0,800,600]]
    if fault=='text':args['expected_text']='anything'
    if fault=='proof':args['focused_edit']={}
    if fault=='stale':args['snapshot_id']='old'
    if fault=='nan':args['x']=float('nan')
    if fault=='missing':del args['y']
    if fault=='phase':t.phase='INPUT_OBSERVED'
    assert service('focus_input',args,**changes)[0]==409
    assert len(calls)==2 and t.stopped.is_set()
