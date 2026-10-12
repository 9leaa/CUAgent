"""Authenticated loopback and original ledger; simulated Driver, no VM/model."""
from functools import partial
import pytest
import test_calc_input_model_task as model
from test_calc_input_model_task import adapter, state
from test_calc_model_http import service as original_service
from test_calc_activation import bind


@pytest.fixture
def activated(tmp_path,state,request,monkeypatch):
    monkeypatch.setattr(model,'CalcInputModelTask',partial(model.CalcInputModelTask,activation_approved=True))
    yield from model.adapter.__wrapped__(tmp_path,state,request,monkeypatch)


@pytest.fixture
def service(activated):
    yield from original_service.__wrapped__(activated)


def selected(setup):
    t,calls=bind(setup)
    t.observe();t.select_cell(dict(snapshot_id=t.snapshot['snapshot_id']))
    return t,calls,dict(snapshot_id=t.snapshot['snapshot_id'])


def test_explicit_activation_returns_fresh_proof_without_input(activated,service):
    t,calls,args=selected(activated)
    code,value=service('activate_window',args)
    assert code==200 and value['status']=='WINDOW_ACTIVATION_OBSERVED'
    assert value['confirmation']['snapshot_id']==value['state']['snapshot_id']!=args['snapshot_id']
    assert not value['confirmation']['inputPermitted'] and not value['confirmation']['commitPermitted']
    assert value['businessStatus']=='UNVERIFIED' and t.used==4 and t.phase=='CONFIRMED'
    assert [k for k,_ in calls]==['get_window_state','get_window_state','bring_to_front','get_window_state']
    assert service('activate_window',dict(snapshot_id=t.snapshot['snapshot_id']))[0]==409
    assert len(calls)==4 and t.stopped.is_set()


@pytest.mark.parametrize('change',[{'pid':10},{'window_id':20},{'activation_approved':True},
    {'name_box_index':2},{'x':10,'y':20},{'snapshot_id':'stale'}])
def test_model_cannot_supply_authority_or_target(activated,service,change):
    t,calls,args=selected(activated);args.update(change)
    assert service('activate_window',args)[0]==409
    assert len(calls)==2 and t.stopped.is_set()


def test_default_input_http_has_no_activation_operation(adapter):
    t,calls,args=selected(adapter)
    generator=original_service.__wrapped__(adapter);request=next(generator)
    try:assert request('activate_window',args)[0]==409
    finally:
        with pytest.raises(StopIteration):next(generator)
    assert len(calls)==2 and t.stopped.is_set()


def test_activation_timeout_never_observes_or_retries(activated,service):
    t,calls,args=selected(activated)
    bind(activated,error=TimeoutError('uncertain'))
    assert service('activate_window',args)[0]==409
    assert t.uncertain and t.stopped.is_set() and len(calls)==3
    assert service('activate_window',args)[0]==409 and len(calls)==3
