"""Complete original producer, synthetic official exchanges; not real acceptance."""
import copy
import json
import pytest
from backend.tests.test_handoff_submit_evidence import test_handoff_trace, test_handoff_exchanges
from backend.tests.test_handoff_result import fixture, RUN, SESSION
from backend.handoff_document import expected_document
from backend.handoff_result import canonical
from handoff_trace import verify_handoff_trace
from handoff_exchanges import match_handoff_exchanges


@pytest.fixture
def checked_evidence():
    source, report = fixture()
    f = test_handoff_trace.HandoffTraceTests()
    f.run_id, f.draft_session_id = RUN, SESSION
    f.material_bytes = canonical(source.model_dump(mode='json'))
    f.document_bytes = expected_document(source, report, run_id=RUN, session_id=SESSION)
    f.draft_args = [{'raw': json.dumps(report)}]
    f.submit_report, f.draft_input_mode = report, 'checked-draft-v1'
    f.setUp()
    try:
        e = test_handoff_exchanges.HandoffExchangeTests()
        e.execution_fixture = f; e.setUp()
        yield f.rows, e.rows, dict(run_id=RUN, session_id=SESSION, materials=f.material_bytes,
            expected=f.document_bytes, draft_input_mode='checked-draft-v1')
    finally:
        f.doCleanups()


def test_complete_producer_and_full_exchange_match_without_business_claim(checked_evidence):
    trace, official, options = checked_evidence
    original = copy.deepcopy((trace, official))
    result = verify_handoff_trace(trace, **options)
    assert result['rawCalls'] == 17 and result['inputMode'] == 'checked-draft-v1'
    assert not any(result[k] for k in ('filesVerified','sessionVerified','semanticVerified'))
    result = match_handoff_exchanges(official, trace, **options)
    assert result['officialToolCalls'] == 12 and result['inputMode'] == 'checked-draft-v1'
    assert not any(result[k] for k in ('imageBytesVerified','sessionVerified','semanticVerified'))
    assert (trace, official) == original


def test_checked_input_full_thirty_raw_includes_worst_case_reopen_queries():
    source, report = fixture()
    f = test_handoff_trace.HandoffTraceTests()
    f.run_id, f.draft_session_id = RUN, SESSION
    f.material_bytes = canonical(source.model_dump(mode='json'))
    f.document_bytes = expected_document(source, report, run_id=RUN, session_id=SESSION)
    f.draft_args, f.submit_report = [{'raw': json.dumps(report)}], report
    f.draft_input_mode, f.extra_reads, f.poll_delays = 'checked-draft-v1', 9, 2
    try:
        f.setUp()
        result = verify_handoff_trace(f.rows, run_id=RUN, session_id=SESSION,
            materials=f.material_bytes, expected=f.document_bytes, draft_input_mode='checked-draft-v1')
        assert result['rawCalls'] == 30
    finally:
        f.doCleanups()


@pytest.mark.parametrize('fault', ['default','unknown_mode','missing','duplicate','mode','extra',
    'digest','body','budget','bool_budget','snapshot','token','index','bool_index','text_arg','after_input',
    'disabled','wrong_parent','bool_parent','cycle','missing_draft','missing_submit','changed_display'])
def test_selection_cannot_be_inferred_replaced_or_detached(checked_evidence, fault):
    trace, official, options = checked_evidence
    select = next(r for r in trace if r['event'] == 'checked_draft_input_intent')
    if fault == 'default': options.pop('draft_input_mode')
    elif fault == 'unknown_mode': options['draft_input_mode']='guess'
    elif fault == 'missing': trace.remove(select)
    elif fault == 'duplicate': trace.insert(trace.index(select),copy.deepcopy(select))
    elif fault == 'mode': select['mode']='literal-text'
    elif fault == 'extra': select['extra']=True
    elif fault == 'digest': select['args']['documentSha256']='0'*64
    elif fault == 'body': select['resolvedText']+='changed'
    elif fault == 'budget': select['used']-=1
    elif fault == 'bool_budget': select['used']=True
    elif fault == 'snapshot': select['args']['snapshot_id']='other'
    elif fault == 'token': select['args']['element_token']='other'
    elif fault == 'index': select['args']['element_index']=100
    elif fault == 'bool_index': select['args']['element_index']=True
    elif fault == 'text_arg': select['args']['text']=options['expected'].decode()
    elif fault == 'after_input':
        index=trace.index(select); trace[index],trace[index+1]=trace[index+1],trace[index]
    elif fault in ('disabled','wrong_parent','bool_parent','cycle'):
        state=next(r['value'] for r in trace if r.get('tool')=='get_window_state' and r['event']=='result')
        if fault=='disabled':state['elements'][1]['enabled']=False
        elif fault=='wrong_parent':state['elements'][1]['parent_index']=999
        elif fault=='bool_parent':state['elements'][1]['parent_index']=True
        else:state['elements'][1]['parent_index']=2
    elif fault in ('missing_draft','missing_submit'):
        tool='check_draft' if fault=='missing_draft' else 'submit_handoff'
        trace[:]=[r for r in trace if r.get('tool')!=tool]
    else:
        state=[r['value'] for r in trace if r.get('tool')=='get_window_state' and r['event']=='result'][-1]
        state['elements'][1]['value']='changed'
    with pytest.raises(ValueError): verify_handoff_trace(trace, **options)
    with pytest.raises(ValueError): match_handoff_exchanges(official, trace, **options)


@pytest.mark.parametrize('fault',['name','digest','snapshot','token','extra_text','result','error'])
def test_official_selection_and_response_are_matched_exactly(checked_evidence,fault):
    trace, official, options = checked_evidence
    call=next(r for r in official if r['type']=='tool/call' and r['data']['name']=='vm_type_checked_draft')
    result=official[official.index(call)+1]['data']['message']
    args=json.loads(call['data']['arguments'])
    if fault=='name':call['data']['name']='vm_type'
    elif fault=='digest':args['documentSha256']='0'*64
    elif fault=='snapshot':args['snapshot_id']='other'
    elif fault=='token':args['element_token']='other'
    elif fault=='extra_text':args['text']=options['expected'].decode()
    elif fault=='result':result['content'][0]['text']='{"ok":false}'
    else:result['isError']=True
    call['data']['arguments']=json.dumps(args)
    assert verify_handoff_trace(trace, **options)['status']=='TRACE_VERIFIED'
    with pytest.raises(ValueError):match_handoff_exchanges(official,trace,**options)
