"""Real authenticated loopback HTTP; simulated Driver and no model inference."""
import pytest
from test_calc_input_model_task import adapter, prepare, state
from test_calc_model_http import service as original_service


@pytest.fixture
def service(adapter):
    yield from original_service.__wrapped__(adapter)


@pytest.mark.parametrize('adapter',[True],indirect=True)
def test_input_and_commit_over_original_authenticated_http(adapter,service,monkeypatch):
    task,calls,*_=adapter;args=prepare(task,monkeypatch)
    code,value=service('input_cell',args)
    assert code==200 and value['protocol']=='calc-input-v1' and value['status']=='INPUT_OBSERVED'
    code,value=service('commit_cell',dict(snapshot_id=value['state']['snapshot_id']))
    assert code==200 and value['status']=='COMMIT_ATTEMPT_OBSERVED'
    assert task.used==7 and task.stopped.is_set() and len(calls)==7
    assert service('input_cell',args)[0]==409 and len(calls)==7


@pytest.mark.parametrize('fault',['session','run','target','raw','save'])
def test_input_http_scope_refusals(adapter,service,monkeypatch,fault):
    task,calls,*_=adapter;args=prepare(task,monkeypatch);changes={};op='input_cell'
    if fault=='session':changes['sessionId']='other'
    elif fault=='run':changes['runId']='other'
    elif fault=='target':args['name_box_index']=2
    elif fault=='raw':op='type_text'
    elif fault=='save':op='save'
    assert service(op,args,**changes)[0]==409
    assert task.stopped.is_set() and len(calls)==3
