"""Trusted save launch configuration; no real VM or model calls."""
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calc_model_guest import save_binding
from calc_runtime import CalcGuestRuntime
from calc_save import workbook_destination
from desktop_control import LeaseController
from test_calc_save_model_task import adapter

RUN='calc-select-11111111-2222-3333-4444-555555555555'


def test_save_is_explicit_and_derived():
    assert save_binding(SimpleNamespace(),None) is None
    args=SimpleNamespace(run=RUN,approve_save=True,save_toolbar_region=[100,20,250,90])
    binding=save_binding(args,dict(commit_approved=True))
    assert binding['destination']==workbook_destination(RUN)
    args.save_toolbar_region[0]=0
    assert binding['toolbar_region'][0]==100


@pytest.mark.parametrize('fault',['approval','input','commit','region','nan','run'])
def test_partial_save_launch_rejected(fault):
    args=SimpleNamespace(run=RUN,approve_save=True,save_toolbar_region=[100,20,250,90])
    inputs=dict(commit_approved=True)
    if fault=='approval':args.approve_save=False
    elif fault=='input':inputs=None
    elif fault=='commit':inputs['commit_approved']=False
    elif fault=='region':args.save_toolbar_region=None
    elif fault=='nan':args.save_toolbar_region[0]=float('nan')
    elif fault=='run':args.run='other'
    with pytest.raises(ValueError):save_binding(args,inputs)


def config(task):
    return dict(selection=dict(pid=task.pid,window_id=task.window,title='Untitled 1',cell=task.cell,
        grid=list(task.grid),session_id=task.session_id,name_box_grid=list(task.name_box_grid)),
        input_binding=dict(input_approved=True,overwrite_disposable=True,approved_text=task.input_text,
            approved_kind=task.input_kind,commit_approved=True,**task.input_regions),
        save_binding=dict(save_approved=True,destination=task.destination,toolbar_region=list(task.toolbar_region)))


def test_runtime_freezes_save_binding_and_keeps_original_lease(adapter,monkeypatch):
    task,calls,control,*_=adapter
    controller=LeaseController(task.directory/'runtime-lease.json',run_id=task.run_id,owner='worker',epoch=1,clock=lambda:100)
    task.lease=controller.gate
    factory=Mock(return_value=task)
    monkeypatch.setattr('calc_runtime.CalcSaveModelTask',factory)
    options=config(task)
    runtime=CalcGuestRuntime(task.directory,controller,model_token='m'*43,control_token='c'*43,
        loopback_test=True,port=0,**options)
    options['save_binding']['toolbar_region'][0]=0
    options['save_binding']['destination']='/tmp/other.ods'
    factory.assert_not_called()
    assert controller.existing() is None
    controller.renew(1)
    try:
        assert runtime.activate()['active']
        assert factory.call_args.kwargs['destination']==task.destination
        assert factory.call_args.kwargs['toolbar_region'][0]==100
        assert len(calls)==1  # Constructor/activation did not observe or act.
        intent=json.loads((task.directory/'calc-activation-intent.json').read_text())
        assert intent['saveBinding']['destination']==task.destination
    finally:runtime.close()
    assert controller.existing()['stopped']


@pytest.mark.parametrize('fault',['extra','path','approval','commit','input','region'])
def test_runtime_rejects_bad_save_binding_before_activation(adapter,fault):
    task,calls,control,*_=adapter
    controller=LeaseController(control,run_id=task.run_id,owner='worker',epoch=1,clock=lambda:100)
    options=config(task)
    if fault=='extra':options['save_binding']['destination_check']='bypass'
    elif fault=='path':options['save_binding']['destination']='/tmp/other.ods'
    elif fault=='approval':options['save_binding']['save_approved']=False
    elif fault=='commit':options['input_binding']['commit_approved']=False
    elif fault=='input':options['input_binding']=None
    elif fault=='region':options['save_binding']['toolbar_region']=[0,0,0,0]
    with pytest.raises(ValueError):
        CalcGuestRuntime(task.directory,controller,model_token='m'*43,control_token='c'*43,**options)
    assert len(calls)==1 and not (task.directory/'calc-activation-intent.json').exists()
