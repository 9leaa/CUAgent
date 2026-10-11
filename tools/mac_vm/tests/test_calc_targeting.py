"""Synthetic routing tests, not model vision or real Calc input evidence."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calc_targeting import plan_cell_target, confirm_selected_cell


@pytest.fixture
def state():
    return dict(pid=10, window_id=20, app_name='LibreOffice', window_title='probe',
                snapshot_id='new', screenshot_frame_valid=True, screenshot_width=800,
                screenshot_height=600, screenshot_scale=2, elements_complete=True,
                window_bounds=dict(x=100, y=50, width=400, height=300), elements=[
                    dict(element_index=0, role='AXWindow', label='probe'),
                    dict(element_index=1, parent_index=0, role='AXTextField', label='A1',
                         element_token='new:1', enabled=True, frame=dict(x=120,y=100,w=50,h=20)),
                    dict(element_index=2, parent_index=0, role='AXComboBox', value='A1', enabled=True),
                    dict(element_index=3, parent_index=2, role='AXTextArea', value='A1', enabled=True),
                ])


def plan(state, **overrides):
    return plan_cell_target(state, **(dict(cell='A1',pid=10,window_id=20,title='probe',
                        observed_at=10,now=11,grid=(0,80,700,550)) | overrides))


def confirm(state, **overrides):
    return confirm_selected_cell(state, **(dict(cell='A1',pid=10,window_id=20,title='probe',
                observed_at=10,now=11,previous_snapshot_id='old',name_box_index=2) | overrides))


def test_unique_ax_preferred(state):
    result = plan(state)
    assert result['route'] == 'ax'
    assert result['target'] == dict(element_index=1,element_token='new:1')
    assert result['requiresPostClickObservation'] and not result['inputPermitted']


@pytest.mark.parametrize('fault', ['incomplete','missing','duplicate','disabled','wrong-parent',
                                    'cycle','bad-token','off-grid','menu','duplicate-index'])
def test_ax_limitations_request_screenshot_instead_of_blocking(state, fault):
    e = state['elements'][1]
    if fault == 'incomplete': state['elements_complete'] = False
    elif fault == 'missing': state['elements'].remove(e)
    elif fault == 'duplicate': state['elements'].append(e | dict(element_index=4,element_token='new:4'))
    elif fault == 'disabled': e['enabled'] = False
    elif fault == 'wrong-parent': e['parent_index'] = 99
    elif fault == 'cycle': e['parent_index'] = 1
    elif fault == 'bad-token': e['element_token'] = ''
    elif fault == 'off-grid': e['frame']['x'] = 900
    elif fault == 'menu': state['elements'][0]['role'] = 'AXMenuBar'
    elif fault == 'duplicate-index': state['elements'].append(dict(e))
    assert plan(state)['status'] == 'NEEDS_SCREENSHOT_POINT'
    result = plan(state,point=dict(snapshot_id='new',x=90,y=120))
    assert result['route'] == 'screenshot' and result['status'] == 'TARGET_PLANNED'
    assert result['target'] == dict(x=90,y=120)
    assert result['coordinateSpace'] == 'window_screenshot_pixels'
    assert not result['inputPermitted']


@pytest.mark.parametrize('key,value', [('pid',True),('pid',99),('window_id',99),
    ('window_title','other'),('app_name','TextEdit'),('snapshot_id',''),
    ('screenshot_frame_valid',False),('screenshot_width',True),('screenshot_width',7999),
    ('screenshot_height',0),('screenshot_scale',float('nan')),('screenshot_scale',False)])
def test_invalid_observation_cannot_fallback(state,key,value):
    state[key] = value
    with pytest.raises(ValueError): plan(state)


@pytest.mark.parametrize('now', [41,9,float('nan'),float('inf'),True])
def test_stale_or_invalid_time_denied(state,now):
    with pytest.raises(ValueError): plan(state,now=now)


@pytest.mark.parametrize('point', [dict(snapshot_id='old',x=90,y=120),
    dict(snapshot_id='new',x=True,y=120),dict(snapshot_id='new',x=float('nan'),y=120),
    dict(snapshot_id='new',x=90,y=79),dict(snapshot_id='new',x=700,y=120),
    dict(snapshot_id='new',x=90,y=550),dict(snapshot_id='new',x=90,y=120,text='bad')])
def test_bad_visual_point_denied(state,point):
    state['elements_complete'] = False
    with pytest.raises(ValueError): plan(state,point=point)


@pytest.mark.parametrize('grid', [None,(0,0,0,1),(0,0,900,600),(0,0,800,601),
                                 (0,0,float('inf'),100),(False,0,100,100)])
def test_invalid_trusted_grid_denied(state,grid):
    with pytest.raises(ValueError): plan(state,grid=grid)


@pytest.mark.parametrize('cell', ['a1','A0','A1:B2','=A1','A1\n','',None])
def test_only_single_canonical_cell(state,cell):
    with pytest.raises(ValueError): plan(state,cell=cell)


def test_partial_ax_name_box_confirmation_is_not_input_permission(state):
    state['elements_complete'] = False
    result = confirm(state)
    assert result['status'] == 'SELECTION_OBSERVED'
    assert not result['inputPermitted'] and not result['inputEffectVerified']


@pytest.mark.parametrize('fault', ['old','wrong-cell','missing-child','wrong-child','duplicate-child',
                                  'wrong-role','wrong-window','bad-index','stale'])
def test_click_needs_new_matching_name_box(state,fault):
    args = {}
    if fault == 'old': args['previous_snapshot_id'] = 'new'
    elif fault == 'wrong-cell': state['elements'][2]['value'] = 'B1'
    elif fault == 'missing-child': state['elements'].pop()
    elif fault == 'wrong-child': state['elements'][3]['value'] = 'B1'
    elif fault == 'duplicate-child': state['elements'].append(state['elements'][3] | dict(element_index=4))
    elif fault == 'wrong-role': state['elements'][2]['role'] = 'AXTextArea'
    elif fault == 'wrong-window': state['elements'][0]['label'] = 'other'
    elif fault == 'bad-index': args['name_box_index'] = True
    elif fault == 'stale': args['now'] = 41
    with pytest.raises(ValueError): confirm(state,**args)
