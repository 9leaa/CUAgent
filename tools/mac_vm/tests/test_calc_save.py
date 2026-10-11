"""Synthetic save policy; no GUI action, path admission or disk write."""
import copy
import pytest
from calc_save import plan_open_save, workbook_destination
from test_calc_input import fixture


def setup():
    s,a=fixture();a['title']='Untitled 1';s['window_title']='Untitled 1';s['elements'][0]['label']='Untitled 1'
    s['elements'][1]['value']='AbZ中文'
    run='calc-select-11111111-2222-3333-4444-555555555555'
    a.update(run_id=run,destination=workbook_destination(run),save_approved=True,toolbar_region=[100,20,250,90])
    s['elements'].append(dict(element_index=4,parent_index=0,role='AXMenuButton',label='Save',enabled=True,
        actions=['AXPress'],element_token='s00000002:4',frame=dict(x=160,y=65,w=30,h=20)))
    return s,a


def test_save_plan_is_not_save_or_path_admission():
    s,a=setup();before=copy.deepcopy(s);r=plan_open_save(s,**a)
    assert r['target']=={'element_token':'s00000002:4'} and r['destination']==a['destination']
    assert not r['savePermitted'] and not r['saved'] and not r['filesystemAdmissionVerified']
    assert s==before and r['commitEvidence']['commitEffectVerified']


@pytest.mark.parametrize('fault',['approval','path','run','title','value','edit','dialog','missing','duplicate',
    'disabled','press','token','frame','outside','menu','region','old'])
def test_save_rejects_uncertain_or_unapproved_target(fault):
    s,a=setup();e=s['elements'][-1]
    if fault=='approval':a['save_approved']=False
    elif fault=='path':a['destination']='/Users/mvpagent/Documents/other.ods'
    elif fault=='run':a['run_id']='../escape'
    elif fault=='title':a['title']='existing.ods'
    elif fault=='value':s['elements'][1]['value']='wrong'
    elif fault in ('edit','dialog'):s['elements'].append(dict(element_index=5,parent_index=0,role='AXSheet' if fault=='dialog' else 'AXButton',label='Accept',enabled=True))
    elif fault=='missing':s['elements'].pop()
    elif fault=='duplicate':s['elements'].append(dict(e,element_index=5,element_token='s00000002:5'))
    elif fault=='disabled':e['enabled']=False
    elif fault=='press':e['actions']=[]
    elif fault=='token':e['element_token']='s00000001:4'
    elif fault=='frame':e['frame']['w']=float('nan')
    elif fault=='outside':e['frame']['x']=400
    elif fault=='menu':e['role']='AXMenuItem'
    elif fault=='region':a['toolbar_region']=[0,0,900,700]
    elif fault=='old':a['now']=131
    with pytest.raises(ValueError):plan_open_save(s,**a)
