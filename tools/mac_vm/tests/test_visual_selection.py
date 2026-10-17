"""Original ledger integration with synthetic OCR; real OCR evidence is separate."""
import copy
import hashlib
import struct
from functools import partial
import pytest
import test_calc_input_task as base
from test_calc_targeting import state
from test_calc_edit import fixture
from test_calc_input_model_task import prepare
from calc_input_model_task import CalcInputModelTask
from visual_selection import confirm_visual_selection


@pytest.fixture
def visual_adapter(tmp_path,state,request,monkeypatch):
    _,regions=fixture()
    state['elements'][2]['frame']=dict(x=110,y=60,w=80,h=20)
    state['elements'].pop(3)  # Name-box child omitted by a partial walk.
    monkeypatch.setattr(base,'CalcInputTask',partial(CalcInputModelTask,
        session_id='session-22222222-2222-2222-2222-222222222222',name_box_grid=[0,0,300,80],
        visual_selection=True,controls_region=regions['controls_region'],editor_regions=regions['editor_regions']))
    def recognize(png,**kwargs):
        w,h=struct.unpack('>II',png[16:24])
        return dict(version=1,engine='AppleVision',sha256=hashlib.sha256(png).hexdigest(),
                    width=w,height=h,items=[dict(text='A1',confidence=1,rect=[20,20,30,20])])
    monkeypatch.setattr('visual_selection.recognize_png',recognize)
    yield from base.input_setup.__wrapped__(tmp_path,state,request)


@pytest.mark.parametrize('visual_adapter',[True],indirect=True)
def test_partial_name_box_does_not_reblock_input_or_commit(visual_adapter,monkeypatch):
    t,calls,*_=visual_adapter
    args=prepare(t,monkeypatch)
    result=t.input_cell(args)
    assert result['status']=='INPUT_OBSERVED'
    result=t.commit_cell(dict(snapshot_id=result['state']['snapshot_id']))
    assert result['status']=='COMMIT_ATTEMPT_OBSERVED' and t.used==7
    assert [tool for tool,_ in calls].count('type_text')==1
    assert t.stopped.is_set()


@pytest.mark.parametrize('fault',['disabled','contradiction','complete','stale','wrong_ocr','timeout'])
def test_fallback_never_bypasses_conflicts_or_missing_proof(visual_adapter,monkeypatch,fault):
    t,calls,s,*_=visual_adapter
    if fault=='disabled':t.visual_selection=False
    if fault=='contradiction':s['elements'][2]['value']='B2'
    if fault=='complete':s['elements_complete']=True
    if fault=='wrong_ocr':
        original=__import__('visual_selection').recognize_png
        def wrong(*args,**kwargs):
            report=original(*args,**kwargs);report['items'][0]['text']='B2';return report
        monkeypatch.setattr('visual_selection.recognize_png',wrong)
    if fault=='timeout':
        def timeout(*args,**kwargs):raise TimeoutError('OCR deadline')
        monkeypatch.setattr('visual_selection.recognize_png',timeout)
    first=t.observe()
    args=dict(snapshot_id=first['state']['snapshot_id'],x=90,y=120)
    if fault=='stale':args['snapshot_id']='old'
    with pytest.raises((ValueError,TimeoutError)):t.select_cell(args)
    assert not any(tool=='type_text' for tool,_ in calls)


def test_original_window_and_freshness_rechecked_even_with_cached_pixels(visual_adapter):
    t,*_=visual_adapter;t.observe();s=copy.deepcopy(t.snapshot)
    context=dict(cell='A1',pid=10,window_id=20,title='probe',observed_at=10,now=11,
                 previous_snapshot_id='old',name_box_index=2)
    cache={};confirm_visual_selection(s,region=t.name_box_grid,cache=cache,**context)
    for changes in [dict(now=41),dict(window_id=99),dict(previous_snapshot_id=s['snapshot_id'])]:
        with pytest.raises(ValueError):
            confirm_visual_selection(s,region=t.name_box_grid,cache=cache,**(context|changes))
