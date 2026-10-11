"""Pure synthetic policy tests, not real Calc input verification."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calc_input import plan_cell_input, validate_cell_payload


def fixture():
    s=dict(pid=10,window_id=20,app_name='LibreOffice',window_title='probe',snapshot_id='s00000002',
           screenshot_width=800,screenshot_height=600,screenshot_scale=2,screenshot_frame_valid=True,
           window_bounds=dict(x=100,y=50,width=400,height=300),elements_complete=False,
           elements=[dict(element_index=0,role='AXWindow',label='probe'),
                     dict(element_index=1,parent_index=0,role='AXTextField',label='A2',enabled=True,
                          element_token='s00000002:1',frame=dict(x=110,y=150,w=40,h=12)),
                     dict(element_index=2,parent_index=0,role='AXComboBox',value='A2',enabled=True),
                     dict(element_index=3,parent_index=2,role='AXTextArea',value='A2',enabled=True)])
    a=dict(cell='A2',pid=10,window_id=20,title='probe',observed_at=100,now=101,
           previous_snapshot_id='s00000001',name_box_index=2,grid=[0,180,150,250],
           approved=True,overwrite_disposable=True,text='AbZ中文',kind='text',
           approved_text='AbZ中文',approved_kind='text')
    return s,a


@pytest.mark.parametrize('text,kind',[('AbZ中文','text'),('2026-10-11','text'),
    ('0','decimal'),('-12.30','decimal'),('999999999999.99','decimal')])
def test_valid_payload_preserved(text,kind):
    assert validate_cell_payload(text,kind)==text


@pytest.mark.parametrize('text,kind',[('=1+1','text'),('+SUM(A1)','text'),('-1','text'),
    ('@x','text'),("'x",'text'),(' x','text'),('x ','text'),('a\tb','text'),('a\nb','text'),
    ('a\x00b','text'),('a\u202eb','text'),('a\u2028b','text'),('','text'),('汉'*86,'text'),
    ('01','decimal'),('+1','decimal'),('1e2','decimal'),('1,2','decimal'),('1.234','decimal'),
    ('１２','decimal'),('1000000000000','decimal'),('1','formula'),(None,'text')])
def test_unsafe_payload_refused(text,kind):
    with pytest.raises(ValueError):validate_cell_payload(text,kind)


def test_plan_is_not_authority_or_storage_confirmation():
    s,a=fixture(); before=copy.deepcopy(s)
    result=plan_cell_input(s,**a)
    assert result['target']=={'element_token':'s00000002:1'}
    assert result['text']=='AbZ中文' and result['requiresPostActionObservation']
    assert not result['inputPermitted'] and not result['inputEffectVerified']
    assert result['businessStatus']=='UNVERIFIED' and s==before


@pytest.mark.parametrize('fault',[None,'missing','duplicate','token','outside','window','disabled','region','selected'])
def test_explicit_formula_target(fault):
    s,a=fixture();a['formula_region']=[200,40,700,90]
    editor=dict(element_index=4,parent_index=0,role='AXTextArea',enabled=True,
                element_token='s00000002:4',frame=dict(x=220,y=75,w=1,h=12))
    if fault!='missing':s['elements'].append(editor)
    if fault=='duplicate':s['elements'].append(dict(editor,element_index=5,element_token='s00000002:5'))
    if fault=='token':editor['element_token']='s00000001:4'
    if fault=='outside':editor['frame']['w']=400
    if fault=='window':editor['parent_index']=99
    if fault=='disabled':editor['enabled']=False
    if fault=='region':a['formula_region']=[200,40,900,90]
    if fault=='selected':s['elements'][2]['value']='B2'
    if fault:
        with pytest.raises(ValueError):plan_cell_input(s,**a)
    else:
        result=plan_cell_input(s,**a)
        assert result['target']==dict(element_token='s00000002:4')
        assert result['text']=='AbZ中文' and not result['inputEffectVerified']


@pytest.mark.parametrize('fault',['approval','overwrite','payload','kind','namebox','child',
    'old_snapshot','expired','pid','token','frame','grid','duplicate','missing','menu','edit'])
def test_uncertain_target_or_authority_refused(fault):
    s,a=fixture()
    if fault=='approval':a['approved']=1
    elif fault=='overwrite':a['overwrite_disposable']=False
    elif fault=='payload':a['text']='abz中文'
    elif fault=='kind':a['kind']='decimal'
    elif fault=='namebox':s['elements'][2]['value']='B2'
    elif fault=='child':s['elements'][3]['value']='A1'
    elif fault=='old_snapshot':a['previous_snapshot_id']=s['snapshot_id']
    elif fault=='expired':a['now']=131
    elif fault=='pid':s['pid']=11
    elif fault=='token':s['elements'][1]['element_token']='s00000001:1'
    elif fault=='frame':s['elements'][1]['frame']['x']=float('nan')
    elif fault=='grid':a['grid']=[200,200,300,300]
    elif fault=='duplicate':s['elements'].append(dict(s['elements'][1],element_index=4))
    elif fault=='missing':s['elements'].pop(1)
    elif fault=='menu':s['elements'][0]['role']='AXMenu'
    elif fault=='edit':s['elements'].append(dict(element_index=4,parent_index=0,role='AXButton',label='Accept',enabled=True))
    with pytest.raises(ValueError):plan_cell_input(s,**a)
