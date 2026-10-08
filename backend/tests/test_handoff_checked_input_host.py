"""Independent host projection with original Task and simulated GUI/session."""
import copy
import pytest
from backend.tests.test_handoff_checked_input_evidence import checked_evidence
from backend.tests.test_handoff_result import fixture, RUN, SESSION
from backend.handoff_result import input_digest
from backend.handoff_draft_evidence import verify_draft_evidence
from backend.handoff_submit_evidence import verify_submission_evidence


def check(evidence, **overrides):
    trace, official, options = evidence
    source, report = fixture()
    args = dict(submission=source, run_id=RUN, session_id=SESSION,
        binding=dict(runId=RUN, sessionId=SESSION, inputSha256=input_digest(source)),
        document=options['expected'], draft_input_mode='checked-draft-v1')
    args.update(overrides)
    draft = verify_draft_evidence(trace, official, report=report, **args)
    submitted = verify_submission_evidence(trace, official, **args)
    return draft, submitted


def test_independent_host_recomputes_original_projection_and_final_submission(checked_evidence):
    before = copy.deepcopy(checked_evidence)
    draft, submitted = check(checked_evidence)
    assert draft['inputMode'] == submitted['inputMode'] == 'checked-draft-v1'
    assert draft['documentSha256'] == submitted['documentSha256']
    assert submitted['rawCalls'] == 17
    assert not draft['guiVerified'] and not submitted['semanticVerified']
    assert checked_evidence == before


@pytest.mark.parametrize('fault', ['default','unknown','missing','duplicate','mode','run','text','digest',
    'used','bool_used','args_text','index','snapshot','attempt_hash','attempt_bytes','attempt_bool',
    'response','official_name','official_args','official_result','official_error','official_duplicate',
    'official_early','official_id','official_seq','extra'])
def test_host_draft_and_submit_reject_changed_selection(checked_evidence, fault):
    trace, official, options = checked_evidence
    selection = next(r for r in trace if r.get('event') == 'checked_draft_input_intent')
    attempt = next(r for r in trace if r.get('event') == 'attempted_input')
    raw_result = next(r for r in trace if r.get('event') == 'result' and r.get('tool') == 'type_text')
    call = next(r for r in official if r['type'] == 'tool/call' and r['data']['name'] == 'vm_type_checked_draft')
    result = official[official.index(call) + 1]
    mode = 'checked-draft-v1'
    if fault == 'default': mode = 'literal-text'
    elif fault == 'unknown': mode = 'unknown'
    elif fault == 'missing': trace.remove(selection)
    elif fault == 'duplicate': trace.insert(trace.index(selection),copy.deepcopy(selection))
    elif fault == 'mode': selection['mode'] = 'literal-text'
    elif fault == 'run': selection['run_id'] = 'other'
    elif fault == 'text': selection['resolvedText'] += 'altered'
    elif fault == 'digest': selection['args']['documentSha256'] = '0'*64
    elif fault == 'used': selection['used'] += 1
    elif fault == 'bool_used': selection['used'] = True
    elif fault == 'args_text': selection['args']['text'] = options['expected'].decode()
    elif fault == 'index': selection['args']['element_index'] = True
    elif fault == 'snapshot': selection['args']['snapshot_id'] = 'other'
    elif fault == 'attempt_hash': attempt['sha256'] = '0'*64
    elif fault == 'attempt_bytes': attempt['bytes'] += 1
    elif fault == 'attempt_bool': attempt['bytes'] = True
    elif fault == 'response': raw_result['value'] = dict(status='refused')
    elif fault == 'official_name': call['data']['name'] = 'vm_type'
    elif fault == 'official_args': call['data']['arguments'] = '{}'
    elif fault == 'official_result': result['data']['message']['content'][0]['text'] = '{}'
    elif fault == 'official_error': result['data']['message']['isError'] = True
    elif fault == 'official_duplicate': official.append(copy.deepcopy(result))
    elif fault == 'official_early': official.remove(call); official.insert(0,call)
    elif fault == 'official_id': call['data']['callId'] = 'other'
    elif fault == 'official_seq': result['seq'] = call['seq']
    elif fault == 'extra': selection['extra'] = True
    source, report = fixture()
    args = dict(submission=source,run_id=RUN,session_id=SESSION,
        binding=dict(runId=RUN,sessionId=SESSION,inputSha256=input_digest(source)),
        document=options['expected'],draft_input_mode=mode)
    with pytest.raises(ValueError): verify_draft_evidence(trace,official,report=report,**args)
    with pytest.raises(ValueError): verify_submission_evidence(trace,official,**args)
