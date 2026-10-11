"""Explicit focus policy/executor with simulated Driver only."""
import copy
import pytest
from test_calc_input import fixture
from test_calc_input_task import formula_setup, input_setup, selected
from test_calc_targeting import state
from test_calc_edit import fixture as edit_fixture
from calc_input import plan_formula_focus


@pytest.mark.parametrize('fault',[None,'stale','nan','edge','outside','extra','missing','no_formula','no_value'])
def test_focus_plan_requires_bound_editor_and_current_interior_point(fault):
    s,a=fixture();a['formula_region']=[200,40,700,90]
    e=dict(element_index=4,parent_index=0,role='AXTextArea',enabled=True,
        value='old',element_token='s00000002:4',frame=dict(x=220,y=75,w=40,h=12))
    s['elements'].append(e)
    p=dict(snapshot_id=s['snapshot_id'],x=250,y=60)
    if fault=='stale':p['snapshot_id']='old'
    if fault=='nan':p['x']=float('nan')
    if fault=='edge':p['x']=240
    if fault=='outside':p['x']=600
    if fault=='extra':p['token']='anything'
    if fault=='missing':del p['y']
    if fault=='no_formula':a.pop('formula_region')
    if fault=='no_value':e.pop('value')
    if fault:
        with pytest.raises(ValueError):plan_formula_focus(s,point=p,**a)
    else:
        result=plan_formula_focus(s,point=p,**a)
        assert result['target']==dict(x=250,y=60) and result['previousText']=='old'
        assert not result['inputPermitted']


@pytest.mark.parametrize('fault',[None,'unchanged','changed','timeout','stopped','budget','same_snapshot'])
def test_focus_once_requires_independent_edit_evidence(formula_setup,monkeypatch,fault):
    t,calls,s,*_=formula_setup
    s['elements'].append(dict(element_index=20,parent_index=0,role='AXTextArea',enabled=True,
        value='a',frame=dict(x=300,y=65,w=10,h=12)))
    selected(t);before=t.snapshot['snapshot_id'];original=t.transport
    source,regions=edit_fixture();attempt=[False];typed=[False]
    def transport(tool,args):
        if tool=='type_text':typed[0]=True
        if tool=='click':
            attempt[0]=True
            if fault=='timeout':raise TimeoutError('focus timeout')
        result=original(tool,args)
        if tool=='get_window_state' and attempt[0] and fault!='unchanged':
            result['elements']=[e for e in result['elements'] if e['element_index']!=20]
            for item in source['elements'][1:]:
                e=copy.deepcopy(item);e['element_index']+=10
                if e['element_index']==14:e['frame']['y']=65
                if typed[0] and e['role']=='AXTextArea':e['value']='AbZ中文'
                if fault=='changed' and e['role']=='AXTextArea':e['value']='other'
                e['element_token']=result['snapshot_id']+':'+str(e['element_index'])
                result['elements'].append(e)
            if fault=='same_snapshot':result['snapshot_id']=before
        return result
    monkeypatch.setattr(t,'transport',transport)
    args=dict(snapshot_id=before,name_box_index=2,point=dict(snapshot_id=before,x=410,y=40),
        controls_region=regions['controls_region'],editor_regions=[regions['editor_regions'][0],[350,20,700,70]])
    if fault=='stopped':t.stop()
    if fault=='budget':t.used=25
    if fault:
        with pytest.raises(Exception):t.focus_input_once(**args)
        assert t.stopped.is_set()
    else:
        result=t.focus_input_once(**args)
        assert result['status']=='INPUT_FOCUS_OBSERVED' and t.used==5
        assert not result['inputEffectVerified'] and not result['inputPermitted']
        assert calls[3]==('click',dict(pid=10,window_id=20,session='input',x=410,y=40,delivery_mode='foreground'))
        focused_snapshot=t.snapshot['snapshot_id']
        result=t.input_once(snapshot_id=focused_snapshot,name_box_index=2,text='AbZ中文',kind='text')
        confirmation=t.confirm_input(snapshot_id=result['state']['snapshot_id'],name_box_index=2,
            controls_region=args['controls_region'],editor_regions=args['editor_regions'])
        assert confirmation['status']=='INPUT_OBSERVED' and t.used==7
        assert [tool for tool,_ in calls][-4:]==['click','get_window_state','type_text','get_window_state']
        assert calls[5][1]['element_token']==focused_snapshot+':14'
        assert 'x' not in calls[5][1]
    n=len(calls)
    with pytest.raises(Exception):t.focus_input_once(**args)
    assert len(calls)==n


@pytest.mark.parametrize('fault',['stale','missing','changed','no_formula'])
def test_focus_proof_cannot_bypass_pending_edit_verification(fault):
    from calc_input import plan_cell_input
    s,a=fixture();editing,r=edit_fixture()
    for item in editing['elements'][1:]:
        e=copy.deepcopy(item);e['element_index']+=10
        e['element_token']=s['snapshot_id']+':'+str(e['element_index'])
        s['elements'].append(e)
    a['formula_region']=r['editor_regions'][1]
    a['focused_edit']=dict(snapshot_id=s['snapshot_id'],expected_text='a',
        controls_region=r['controls_region'],editor_regions=r['editor_regions'])
    if fault=='stale':a['focused_edit']['snapshot_id']='old'
    if fault=='missing':a['focused_edit']=None
    if fault=='changed':a['focused_edit']['expected_text']='wrong'
    if fault=='no_formula':a.pop('formula_region')
    with pytest.raises(ValueError):plan_cell_input(s,**a)
