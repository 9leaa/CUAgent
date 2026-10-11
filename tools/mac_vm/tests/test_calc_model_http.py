"""Real loopback HTTP and original task ledger; simulated Driver only."""
from functools import partial
import http.client
import json
import secrets
import threading
import pytest
import test_calc_selection
from test_calc_selection import state
from calc_model_task import CalcModelTask,PROTOCOL
from desktop_tools_http import tools_server

SESSION='session-22222222-2222-2222-2222-222222222222'


@pytest.fixture
def model_setup(tmp_path,state,monkeypatch):
    state['elements'][2]['frame']=dict(x=110,y=60,w=80,h=20)
    monkeypatch.setattr(test_calc_selection,'CalcSelectionTask',partial(CalcModelTask,session_id=SESSION,name_box_grid=(0,0,300,80)))
    yield from test_calc_selection.setup.__wrapped__(tmp_path,state,monkeypatch)


@pytest.fixture
def service(model_setup):
    task,*_=model_setup
    token=secrets.token_urlsafe(32)
    server=tools_server(task,token,control_token=secrets.token_urlsafe(32),port=0,loopback_test=True)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01});thread.start()
    def request(op,args=None,**changes):
        body=dict(op=op,args={} if args is None else args,runId=task.run_id,sessionId=SESSION)|changes
        conn=http.client.HTTPConnection(*server.server_address,timeout=3)
        try:
            conn.request('POST','/',json.dumps(body),{'Authorization':'Bearer '+token})
            response=conn.getresponse()
            return response.status,json.loads(response.read())
        finally: conn.close()
    try: yield request
    finally:
        server.shutdown();server.server_close();thread.join(3)


@pytest.mark.parametrize('ax',[True,False])
def test_official_envelope_through_http_to_executor(model_setup,service,ax):
    task,calls,state,*_=model_setup
    state['elements_complete']=ax
    code,value=service('observe')
    assert code==200 and value['protocol']==PROTOCOL and value['sessionId']==SESSION
    args=dict(snapshot_id=value['state']['snapshot_id'])
    if not ax:
        assert service('select_cell',args)[1]['status']=='NEEDS_SCREENSHOT_POINT'
        args.update(x=90,y=120)
    code,value=service('select_cell',args)
    assert code==200 and value['status']=='SELECTION_OBSERVED'
    assert value['businessStatus']=='UNVERIFIED' and value['inputPermitted'] is False
    assert value['confirmation']['snapshot_id']==value['state']['snapshot_id']
    assert task.used==3 and task.stopped.is_set()
    assert service('observe')[0]==409 and len(calls)==3
    assert [c[0] for c in calls]==['get_window_state','click','get_window_state']


@pytest.mark.parametrize('op,args,changes',[
    ('observe',{},dict(sessionId='other')),('observe',{},dict(runId='other')),
    ('type_text',{},{}),('save',{},{}),('confirm',dict(nameBoxIndex=2),{}),
    ('select_cell',dict(snapshot_id='stale',x=90,y=120),{}),
    ('select_cell',dict(snapshot_id='s1',x=90),{}),
    ('select_cell',dict(snapshot_id='s1',x=90,y=120,pid=10),{}),
    ('select_cell',dict(snapshot_id='s1',x=float('nan'),y=120),{}),
])
def test_model_cannot_choose_scope_or_verifier(model_setup,service,op,args,changes):
    task,calls,*_=model_setup
    assert service('observe')[0]==200
    assert service(op,args,**changes)[0]==409
    assert task.used==2 and task.stopped.is_set() and len(calls)==1
    assert task.snapshot is None


@pytest.mark.parametrize('fault',['wrong_value','outside','ambiguous','missing_child'])
def test_independent_confirmation_failure_stops(model_setup,service,fault):
    task,calls,state,*_=model_setup
    assert service('observe')[0]==200
    if fault=='wrong_value': state['elements'][2]['value']='B2'
    if fault=='outside': state['elements'][2]['frame']['x']=400
    if fault=='ambiguous': state['elements'].append(state['elements'][2]|dict(element_index=4))
    if fault=='missing_child': state['elements'].pop(3)
    assert service('select_cell',dict(snapshot_id='s1',x=90,y=120))[0]==409
    assert task.stopped.is_set() and task.used==3 and len(calls)==3
    assert service('select_cell',dict(snapshot_id='s2',x=90,y=120))[0]==409
    assert len(calls)==3


def test_cancel_before_action(model_setup,service):
    task,calls,*_=model_setup
    assert service('observe')[0]==200
    assert service('stop')==(200,dict(stopped=True))
    assert service('select_cell',dict(snapshot_id='s1',x=90,y=120))[0]==409
    assert len(calls)==1
