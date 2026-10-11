"""Synthetic snapshot policy tests; no Driver or model invocation."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calc_edit import plan_edit_cancel


def fixture():
    state=dict(pid=10,window_id=20,app_name='LibreOffice',window_title='probe',snapshot_id='s00000001',
        screenshot_width=800,screenshot_height=600,screenshot_scale=2,screenshot_frame_valid=True,
        window_bounds=dict(x=100,y=50,width=400,height=300),elements_complete=False,
        elements=[dict(element_index=0,role='AXWindow',label='probe')])
    for index,role,label,frame,value in [
        (1,'AXButton','Cancel',dict(x=220,y=100,w=10,h=10),None),
        (2,'AXButton','Accept',dict(x=240,y=100,w=10,h=10),None),
        (3,'AXTextArea','a',dict(x=110,y=150,w=8,h=10),'a'),
        (4,'AXTextArea','a',dict(x=290,y=100,w=8,h=10),'a')]:
        state['elements'].append(dict(element_index=index,element_token=f's00000001:{index}',parent_index=0,
            role=role,label=label,frame=frame,value=value,enabled=True,actions=['AXPress'] if role=='AXButton' else []))
    args=dict(pid=10,window_id=20,title='probe',observed_at=100,now=101,approved=True,expected_text='a',
              controls_region=[200,90,320,130],editor_regions=[[0,190,80,240],[370,90,420,130]])
    return state,args


def test_exact_disposable_input_plans_only_cancel_with_fresh_token():
    s,a=fixture();before=copy.deepcopy(s);p=plan_edit_cancel(s,**a)
    assert p['target']==dict(element_index=1,element_token='s00000001:1')
    assert p['requiresPostActionObservation'] and not p['inputPermitted']
    assert p['businessStatus']=='UNVERIFIED' and s==before


@pytest.mark.parametrize('fault',['approval','text','other_editor','disabled','missing','duplicate',
    'menu','stale_token','stale_time','identity','region','overlap','bad_frame','no_press','extra_editor'])
def test_refuse_uncertain_or_unapproved_cancellation(fault):
    s,a=fixture()
    if fault=='approval':a['approved']=False
    elif fault=='text':a['expected_text']='private'
    elif fault=='other_editor':s['elements'][4]['value']='changed'
    elif fault=='disabled':s['elements'][2]['enabled']=False
    elif fault=='missing':s['elements'].pop(1)
    elif fault=='duplicate':s['elements'].append(dict(s['elements'][1],element_index=8,element_token='s00000001:8'))
    elif fault=='menu':s['elements'][0]['role']='AXMenu'
    elif fault=='stale_token':s['elements'][1]['element_token']='s00000000:1'
    elif fault=='stale_time':a['now']=131
    elif fault=='identity':s['pid']=11
    elif fault=='region':a['controls_region']=[0,0,900,700]
    elif fault=='overlap':a['editor_regions'][1]=a['editor_regions'][0]
    elif fault=='bad_frame':s['elements'][1]['frame']['x']=float('nan')
    elif fault=='no_press':s['elements'][1]['actions']=[]
    elif fault=='extra_editor':s['elements'].append(dict(s['elements'][3],element_index=8,element_token='s00000001:8'))
    with pytest.raises(ValueError):plan_edit_cancel(s,**a)
