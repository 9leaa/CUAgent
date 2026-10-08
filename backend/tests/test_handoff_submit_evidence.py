"""Full original Task with simulated Driver; independent submission gate only."""
import copy
import json
import sys
from pathlib import Path

import pytest
from backend.handoff_document import expected_document
from backend.handoff_result import canonical, input_digest
from backend.handoff_submit_evidence import verify_submission_evidence
from backend.tests.test_handoff_result import fixture, RUN, SESSION

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm/tests'))
import test_handoff_trace
import test_handoff_exchanges


@pytest.fixture
def evidence():
    source, report = fixture()
    f = test_handoff_trace.HandoffTraceTests()
    f.run_id = RUN
    f.material_bytes = canonical(source.model_dump(mode='json'))
    f.document_bytes = expected_document(source, report, run_id=RUN, session_id=SESSION)
    f.draft_session_id = SESSION
    f.draft_args = [{'raw': json.dumps(report)}]
    f.submit_report = report
    f.setUp()
    try:
        e = test_handoff_exchanges.HandoffExchangeTests()
        e.execution_fixture = f; e.setUp()
        yield f.rows, e.rows, dict(submission=source, run_id=RUN, session_id=SESSION,
            binding=dict(runId=RUN, sessionId=SESSION, inputSha256=input_digest(source)),
            document=f.expected)
    finally:
        f.doCleanups()


def test_original_producer_independently_verified_without_full_acceptance(evidence):
    trace, official, kwargs = evidence
    before = copy.deepcopy((trace, official))
    result = verify_submission_evidence(trace, official, **kwargs)
    assert result['status'] == 'SUBMISSION_EVIDENCE_MATCHED' and result['rawCalls'] == 17
    assert not any(result[k] for k in ('sessionVerified', 'guiVerified', 'semanticVerified'))
    assert (trace, official) == before


@pytest.mark.parametrize('fault', ['none', 'arguments', 'response', 'after', 'stop', 'missing_session'])
def test_trace_and_exchanges_new_protocol(evidence, fault):
    from handoff_trace import verify_handoff_trace
    from handoff_exchanges import match_handoff_exchanges
    trace, official, kwargs = evidence
    submits = [r for r in trace if r.get('tool') == 'submit_handoff']
    if fault == 'arguments': submits[1]['args']['report']['tasks'][0]['progress']['text'] = 'changed'
    if fault == 'response': submits[2]['value']['used'] = True
    if fault == 'after': trace.append(dict(submits[0], call_id='later', tool='read_result', used=18))
    if fault == 'stop': trace.insert(trace.index(submits[2]), dict(trace[-1]))
    options = dict(run_id=RUN, materials=canonical(kwargs['submission'].model_dump(mode='json')),
                   expected=kwargs['document'], session_id=None if fault == 'missing_session' else SESSION)
    if fault == 'none':
        assert verify_handoff_trace(trace, **options)['rawCalls'] == 17
        assert match_handoff_exchanges(official, trace, **options)['officialToolCalls'] == 12
    else:
        with pytest.raises(ValueError): verify_handoff_trace(trace, **options)
        with pytest.raises(ValueError): match_handoff_exchanges(official, trace, **options)


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'after', 'stop', 'budget', 'bool_budget',
    'identity', 'report', 'response', 'readback', 'read_tool', 'call_id', 'binding',
    'official_args', 'official_result', 'official_error', 'official_duplicate', 'official_after', 'official_id'])
def test_tampering_missing_evidence_and_post_submit_activity_denied(evidence, fault):
    trace, official, kwargs = evidence
    submit = [r for r in trace if r.get('tool') == 'submit_handoff']
    call, args, result = submit
    if fault == 'missing': trace.remove(args)
    if fault == 'duplicate': trace.append(copy.deepcopy(result))
    if fault == 'after': trace.append(dict(call, call_id='after', used=18, tool='read_result'))
    if fault == 'stop': trace.insert(trace.index(call), dict(event='stop'))
    if fault == 'budget': call['used'] = 31
    if fault == 'bool_budget': trace[next(i for i,r in enumerate(trace) if r.get('event')=='dispatch')]['used'] = True
    if fault == 'identity': args['run_id'] = 'other'
    if fault == 'report': args['args']['report']['tasks'][0]['progress']['text'] = 'changed'
    if fault == 'response': result['value']['reportSha256'] = '0' * 64
    if fault == 'readback':
        next(r for r in trace if r.get('event') == 'result' and r.get('tool') == 'read_result')['value'] = 'wrong'
    if fault == 'read_tool':
        next(r for r in trace if r.get('event') == 'dispatch' and r.get('tool') == 'read_result')['tool'] = 'read_materials'
    if fault == 'call_id': args['call_id'] = 'other'
    if fault == 'binding': kwargs['binding']['sessionId'] = 'wrong'
    if fault == 'official_args': official[-2]['data']['arguments'] = '{}'
    if fault == 'official_result': official[-1]['data']['message']['content'][0]['text'] = '{}'
    if fault == 'official_error': official[-1]['data']['message']['isError'] = True
    if fault == 'official_duplicate': official.extend(copy.deepcopy(official[-2:]))
    if fault == 'official_after':
        row = copy.deepcopy(official[-2]); row['data']['name'] = 'vm_read_result'; official.append(row)
    if fault == 'official_id': official[-1]['data']['message']['toolCallId'] = 'other'
    with pytest.raises(ValueError): verify_submission_evidence(trace, official, **kwargs)
