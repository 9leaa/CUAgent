"""Original ledger and filesystem, simulated exact-window Driver responses."""
import copy
import json
from functools import partial
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calc_input_task import CalcInputTask,verify_window_activation
from driver_smoke import StopRun
import test_calc_input_task as fixtures
from test_calc_input_task import input_setup,selected
from test_calc_targeting import state


def response():
    return dict(status='activated',code='bring_to_front_exact_window_verified',pid=10,window_id=20,
        activated=True,process_activated=True,request_accepted=True,
        exact_window_effect=dict(verified=True,focused=True,front_in_process_on_display=True,
                                target_visible_ordinary=True,frontmost_ordinary=False),
        observed=dict(frontmost_pid=10,focused_window_id=20,process_front_window_on_display=20,
                      front_process_matches_target=True,frontmost_ordinary_window_id=900))


@pytest.fixture
def activation_setup(tmp_path,state,request,monkeypatch):
    monkeypatch.setattr(fixtures,'CalcInputTask',partial(CalcInputTask,activation_approved=True))
    yield from fixtures.input_setup.__wrapped__(tmp_path,state,request)


def bind(setup,value=None,error=None):
    t,calls,*_=setup
    prior=t.transport
    def transport(tool,args):
        if tool=='bring_to_front':
            calls.append((tool,copy.deepcopy(args)))
            if error:raise error
            return copy.deepcopy(response() if value is None else value)
        return prior(tool,args)
    t.transport=transport
    return t,calls


def activate(t):
    return t.activate_window_once(snapshot_id=t.snapshot['snapshot_id'] if t.snapshot else '',name_box_index=2,resolve_name_box=lambda: 2)


def test_single_explicit_action_original_budget_and_new_observation(activation_setup):
    t,calls=bind(activation_setup);selected(t)
    before=t.snapshot['snapshot_id'];out=activate(t)
    assert t.used==5 and out['status']=='WINDOW_ACTIVATION_OBSERVED'
    assert t.snapshot['snapshot_id']!=before and t.phase=='CONFIRMED'
    assert not out['inputPermitted'] and not out['inputEffectVerified']
    assert calls[-2:][0]==('bring_to_front',dict(pid=10,window_id=20,session='input'))
    assert calls[-1][0]=='get_window_state'
    assert json.loads((t.directory/'input-binding.json').read_text())['activationApproved'] is True
    with pytest.raises(FileExistsError):activate(t)
    assert t.used==5 and t.stopped.is_set()


def test_default_mode_denies_activation(input_setup):
    t,calls,*_=input_setup;selected(t)
    with pytest.raises(StopRun):activate(t)
    assert t.used==3 and not any(k=='bring_to_front' for k,_ in calls)
    assert 'bring_to_front' not in t.RAW_TOOLS


@pytest.mark.parametrize('path,value',[
    ('status','partial'),('code','bring_to_front_process_verified'),('activated',1),
    ('process_activated',False),('pid',11),('window_id',21),('pid',True),
    ('exact_window_effect.verified',False),('exact_window_effect.focused',None),
    ('exact_window_effect.front_in_process_on_display',False),
    ('exact_window_effect.target_visible_ordinary',False),
    ('observed.frontmost_pid',11),('observed.focused_window_id',None),
    ('observed.process_front_window_on_display',21),('observed.front_process_matches_target',False),
])
def test_partial_or_mismatched_proof_stops_without_observation(activation_setup,path,value):
    r=response();parts=path.split('.');d=r
    for key in parts[:-1]:d=d[key]
    d[parts[-1]]=value
    t,calls=bind(activation_setup,r);selected(t)
    with pytest.raises(ValueError):activate(t)
    assert t.used==4 and t.uncertain and t.stopped.is_set()
    assert calls[-1][0]=='bring_to_front'


def test_other_display_global_order_not_mistaken_for_focus_failure():
    r=response();r['request_accepted']=False
    assert verify_window_activation(r,10,20)['status']=='WINDOW_ACTIVATION_OBSERVED'


def test_timeout_is_unknown_once(activation_setup):
    t,calls=bind(activation_setup,error=TimeoutError('unknown activation'));selected(t)
    with pytest.raises(TimeoutError):activate(t)
    assert t.used==4 and t.uncertain and t.stopped.is_set()
    with pytest.raises(StopRun):activate(t)
    assert sum(k=='bring_to_front' for k,_ in calls)==1
    rows=[json.loads(line) for line in t.ledger.read_text().splitlines()]
    assert any(r['event']=='UNKNOWN' and r['tool']=='bring_to_front' for r in rows)


@pytest.mark.parametrize('fault',['budget','stopped','expired','stale','audit'])
def test_preconditions_fail_without_dispatch(activation_setup,monkeypatch,fault):
    t,calls=bind(activation_setup);selected(t);before=len(calls)
    if fault=='budget':t.used=23
    elif fault=='stopped':t.stop()
    elif fault=='expired':
        path=activation_setup[3];v=json.loads(path.read_text());v['expiresAt']=99000;path.write_text(json.dumps(v))
    elif fault=='stale':t.observed_at-=100
    elif fault=='audit':
        def reject(*_):raise OSError('disk unavailable')
        monkeypatch.setattr('calc_input_task._save',reject)
    with pytest.raises((StopRun,ValueError,OSError)):activate(t)
    assert len(calls)==before and t.stopped.is_set()


def test_stop_during_activation_does_not_dispatch_post_observation(activation_setup):
    t,calls=bind(activation_setup);selected(t);prior=t.transport
    def transport(tool,args):
        value=prior(tool,args)
        if tool=='bring_to_front':t.stop()
        return value
    t.transport=transport
    with pytest.raises(StopRun):activate(t)
    assert t.used==4 and calls[-1][0]=='bring_to_front'
