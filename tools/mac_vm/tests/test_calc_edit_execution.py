"""Original HTTP/task ledger with simulated Driver; not real GUI evidence."""
from functools import partial
import pytest
import test_calc_selection
from test_calc_selection import state
from test_calc_model_http import SESSION,service
from test_calc_edit import fixture
from calc_model_task import CalcModelTask


@pytest.fixture
def model_setup(tmp_path,state,monkeypatch):
    edit,args=fixture()
    state['elements'][2]['frame']=dict(x=110,y=60,w=80,h=20)
    for element in edit['elements'][1:]:
        state['elements'].append(element | dict(element_index=element['element_index']+10))
    binding={k:args[k] for k in ('approved','expected_text','controls_region','editor_regions')}
    monkeypatch.setattr(test_calc_selection,'CalcSelectionTask',partial(CalcModelTask,
        session_id=SESSION,name_box_grid=(0,0,300,80),edit_cancel=binding))
    for setup in test_calc_selection.setup.__wrapped__(tmp_path,state,monkeypatch):
        task=setup[0];old=task.transport
        def transport(tool,params):
            result=old(tool,params)
            if tool=='get_window_state':
                for e in result['elements']:
                    e['element_token']=result['snapshot_id']+':'+str(e['element_index'])
            return result
        task.transport=transport
        yield setup


def offer(service):
    assert service('observe')[0]==200
    code,result=service('select_cell',dict(snapshot_id='s1'))
    assert code==200 and result['status']=='NEEDS_EDIT_CANCEL' and result['used']==1


def test_cancel_then_fresh_model_point_uses_original_five_raw(model_setup,service):
    task,calls,state,*_=model_setup
    offer(service)
    old=task.transport
    def cancel(tool,args):
        result=old(tool,args)
        if tool=='click' and 'element_index' in args:
            state['elements']=[e for e in state['elements'] if e['element_index']<10]
        return result
    task.transport=cancel
    code,result=service('select_cell',dict(snapshot_id='s1',cancel_edit=True))
    assert code==200 and result['status']=='EDIT_CANCEL_ATTEMPT_OBSERVED'
    assert result['state']['snapshot_id']=='s2' and result['used']==3 and result['png']
    assert not task.stopped.is_set()
    assert calls[1][1]['element_index']==11 and calls[1][1]['element_token']=='s1:11'
    assert service('select_cell',dict(snapshot_id='s2'))[1]['status']=='NEEDS_SCREENSHOT_POINT'
    code,result=service('select_cell',dict(snapshot_id='s2',x=90,y=120))
    assert code==200 and result['status']=='SELECTION_OBSERVED' and task.used==5
    assert task.stopped.is_set() and [c[0] for c in calls]==['get_window_state','click','get_window_state','click','get_window_state']


@pytest.mark.parametrize('fault',['unchanged','unknown','stopped','stale','false','mixed','unapproved','changed','budget'])
def test_failed_cancel_never_replays(model_setup,service,fault):
    task,calls,state,*_=model_setup
    offer(service)
    args=dict(snapshot_id='s1',cancel_edit=True)
    if fault=='unknown':
        old=task.transport
        def timeout(tool,params):
            old(tool,params)
            raise TimeoutError('simulated unknown effect')
        task.transport=timeout
    elif fault=='stopped':task.stop()
    elif fault=='stale':args['snapshot_id']='old'
    elif fault=='false':args['cancel_edit']=False
    elif fault=='mixed':args.update(x=90,y=120)
    elif fault=='unapproved':task.edit_cancel=None
    elif fault=='changed':task.snapshot['elements'][-1]['value']='other'
    elif fault=='budget':
        for _ in range(28):task.observe()
        args['snapshot_id']=task.snapshot['snapshot_id']
    assert service('select_cell',args)[0]==409
    count=len(calls)
    assert task.stopped.is_set()
    assert service('select_cell',args)[0]==409 and len(calls)==count
    if fault=='unchanged':assert task.used==3 and count==3
    elif fault=='unknown':assert task.uncertain and count==2
    elif fault=='budget':assert count==29
    else:assert count==1
