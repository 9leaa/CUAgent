"""Cross-check guest helper with independent host Pydantic gate; no VM/model."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest
from backend.handoff_draft import check_draft
from backend.tests.test_handoff_result import fixture,RUN,SESSION

spec=importlib.util.spec_from_file_location('guest_draft',Path(__file__).resolve().parents[2]/'tools/mac_vm/handoff_draft.py')
guest=importlib.util.module_from_spec(spec);spec.loader.exec_module(guest)


def both(source,data):
    raw=json.dumps(data,ensure_ascii=False)
    return (check_draft(source,raw,run_id=RUN,session_id=SESSION),
            guest.check(source.model_dump(mode='json'),raw,run_id=RUN,session_id=SESSION))


def test_same_accepted_report_exact_canonical_and_document_bytes():
    source,data=fixture();before=copy.deepcopy(data)
    host,vm=both(source,data)
    for key in ('status','semanticVerified','guiVerified','rawSha256','canonicalJson','document','documentSha256'):
        assert host[key]==vm[key]
    assert data==before and vm['status']=='DRAFT_STRUCTURE_VALID'
    assert vm['semanticVerified'] is vm['guiVerified'] is False


@pytest.mark.parametrize('path,value',[
    (['kind'],'other'),(['runId'],RUN+'x'),(['sessionId'],SESSION+'x'),(['inputSha256'],'0'*64),
    (['counts','done'],True),(['counts','todo'],2),(['tasks',0,'owner'],'guess'),
    (['tasks',0,'overdue'],False),(['tasks',0,'task_id'],'invented'),
    (['tasks',0,'progress','text'],' '),(['tasks',0,'handoff','text'],'\x00'),
    (['tasks',0,'progress','citations',0,'start'],True),
    (['tasks',0,'progress','citations',0,'end'],100000),
    (['tasks',0,'progress','citations',0,'quote'],'not original'),
    (['tasks',0,'progress','citations',0,'sourceSha256'],'0'*64),
    (['tasks',0,'progress','citations',0,'sourceId'],'../../secret'),
    (['issues',0,'taskIds'],['a','a']),(['issues',0,'category'],'other'),
    (['issues',0,'taskIds'],['b']),(['issues',2,'citations'],[]),
    (['tasks',0,'progress','text'],'x'*2049)])
def test_independent_gates_both_reject_malformed_or_changed_facts(path,value):
    source,data=fixture();target=data
    for k in path[:-1]:target=target[k]
    target[path[-1]]=value
    host,vm=both(source,data)
    assert host['status']==vm['status']=='DRAFT_REJECTED'
    assert 'document' not in vm


@pytest.mark.parametrize('mode',['missing','duplicate','missing_handoff','extra','missing_issue','duplicate_issue','duplicate_citation'])
def test_collections_and_required_fields(mode):
    source,data=fixture()
    if mode=='missing':data['tasks'].pop()
    if mode=='duplicate':data['tasks'].append(copy.deepcopy(data['tasks'][0]))
    if mode=='missing_handoff':del data['tasks'][0]['handoff']
    if mode=='extra':data['tasks'][0]['extra']='x'
    if mode=='missing_issue':data['issues'].pop(0)
    if mode=='duplicate_issue':data['issues'].append(copy.deepcopy(data['issues'][0]))
    if mode=='duplicate_citation':data['tasks'][0]['progress']['citations']*=2
    host,vm=both(source,data);assert host['status']==vm['status']=='DRAFT_REJECTED'


@pytest.mark.parametrize('raw',['{"x":1,"x":2}','NaN','{"tasks":[}', '[]', '', 'x'*65537,
                               pytest.param('['*2000+']'*2000,id='deep'), '\ud800'])
def test_raw_invalid_no_repair(raw):
    source,_=fixture()
    result=guest.check(source.model_dump(mode='json'),raw,run_id=RUN,session_id=SESSION)
    assert result['status']=='DRAFT_REJECTED' and 'document' not in result


def test_unicode_projection_and_task_order_preserved():
    source,data=fixture()
    data['tasks'].reverse()
    for t in data['tasks']:t['progress']['text']='中文🙂 e\u0301 "引号"\n第二行'
    host,vm=both(source,data)
    assert host['document']==vm['document']
    assert vm['document'].index('[a]')<vm['document'].index('[d]')


def test_oversize_projection_rejected_not_truncated():
    source,data=fixture()
    for t in data['tasks']:t['progress']['text']='中'*680
    host,vm=both(source,data)
    assert host['code']==vm['code']=='DOCUMENT_PROJECTION_LIMIT'
