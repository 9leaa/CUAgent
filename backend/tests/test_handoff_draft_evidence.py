"""Real task preflight audit, synthetic official exchanges; no model or GUI."""
import copy
import json
import pytest
from backend.handoff_draft_evidence import verify_draft_evidence
from backend.handoff_result import input_digest
from backend.tests.test_handoff_draft_task import task
from backend.tests.test_handoff_result import fixture, RUN, SESSION


@pytest.fixture
def evidence(task):
    t, _, report = task
    t.check_draft({'raw': '{broken'})
    accepted = t.check_draft({'raw': json.dumps(report, ensure_ascii=False)})
    trace = [json.loads(line) for line in t.ledger.read_text().splitlines()]
    official = []
    for row in trace:
        if row.get('event') == 'helper_arguments':
            official.append(dict(type='tool/call', seq=len(official), data=dict(name='vm_check_draft',
                callId=row['call_id'], arguments=json.dumps(row['args']))))
        elif row.get('event') == 'result':
            official.append(dict(type='tool/result', seq=len(official), data=dict(message=dict(
                toolCallId=row['call_id'], content=[dict(type='text', text=json.dumps(row['value']))]))))
    # Only the draft gate is under test. Full GUI/trace acceptance remains separate.
    trace.append(dict(event='dispatch', run_id=RUN, tool='type_text', used=3, call_id='input'))
    source, _ = fixture()
    return dict(trace=trace, official=official, submission=source, run_id=RUN, session_id=SESSION,
                binding=dict(runId=RUN, sessionId=SESSION, inputSha256=input_digest(source)),
                report=report, document=accepted['document'].encode())


def test_original_task_audit_independently_recomputed(evidence):
    before = copy.deepcopy(evidence)
    result = verify_draft_evidence(**evidence)
    assert result['status'] == 'DRAFT_EVIDENCE_MATCHED' and result['calls'] == 2
    assert result['semanticVerified'] is result['guiVerified'] is False
    assert evidence == before


@pytest.mark.parametrize('fault', ['session', 'input', 'final', 'document', 'canonical', 'sha',
    'used_bool', 'semantic', 'raw', 'orphan', 'duplicate', 'late', 'official_args', 'official_response',
    'official_duplicate', 'official_error', 'false_valid', 'last_rejected'])
def test_forged_or_mismatched_evidence_refused(evidence, fault):
    e = evidence
    results = [r for r in e['trace'] if r.get('event') == 'result']
    args = [r for r in e['trace'] if r.get('event') == 'helper_arguments']
    value = results[-1]['value']
    if fault == 'session': e['binding']['sessionId'] = 'other'
    if fault == 'input': e['binding']['inputSha256'] = '0' * 64
    if fault == 'final': e['report']['tasks'][0]['progress']['text'] = 'different'
    if fault == 'document': e['document'] += b'\n'
    if fault == 'canonical': value['canonicalJson'] = '{}'
    if fault == 'sha': value['rawSha256'] = '0' * 64
    if fault == 'used_bool': value['used'] = True
    if fault == 'semantic': value['semanticVerified'] = True
    if fault == 'raw': args[-1]['args']['raw'] += ' '
    if fault == 'orphan': args[-1]['call_id'] = 'other'
    if fault == 'duplicate': e['trace'].insert(2, copy.deepcopy(args[-1]))
    if fault == 'late': e['trace'].insert(0, e['trace'].pop())
    if fault == 'official_args': e['official'][-2]['data']['arguments'] = '{"raw":"other"}'
    if fault == 'official_response': e['official'][-1]['data']['message']['content'][0]['text'] = '{}'
    if fault == 'official_duplicate': e['official'].append(copy.deepcopy(e['official'][-1]))
    if fault == 'official_error': e['official'][-1]['data']['message']['isError'] = True
    if fault == 'false_valid': results[0]['value']['status'] = 'DRAFT_STRUCTURE_VALID'
    if fault == 'last_rejected':
        args[-1]['args']['raw'] = '{broken'
        results[-1]['value'] = dict(results[0]['value'], used=2)
    with pytest.raises(ValueError): verify_draft_evidence(**e)
