"""Independent host draft gate; does not replace trace, GUI or session gates."""
import hashlib
from backend.handoff_draft import check_draft
from backend.handoff_result import canonical, input_digest
from backend.handoff_session import strict_json


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_DRAFT_EVIDENCE_UNVERIFIED')


def verify_draft_evidence(trace, official, *, submission, run_id, session_id,
                          binding, report, document, draft_input_mode='literal-text'):
    require(draft_input_mode in ('literal-text', 'checked-draft-v1'))
    require(type(trace) is list and 0 < len(trace) <= 512)
    require(type(official) is list)
    if draft_input_mode == 'literal-text':
        require(not any(r.get('event') == 'checked_draft_input_intent' for r in trace)
                and not any(r.get('type') == 'tool/call' and r.get('data', {}).get('name') ==
                            'vm_type_checked_draft' for r in official))
    digest = input_digest(submission)
    require(binding == dict(runId=run_id, sessionId=session_id, inputSha256=digest))
    draft_rows = [(i, r) for i, r in enumerate(trace) if r.get('tool') == 'check_draft']
    calls = [(i, r) for i, r in draft_rows if r.get('event') == 'dispatch']
    require(0 < len(calls) <= 30)
    require(all(r.get('event') in {'dispatch', 'helper_arguments', 'result'} for _, r in draft_rows))
    all_calls = [r for r in trace if r.get('event') == 'dispatch']
    require(len(all_calls) <= 30)
    require(all(type(r.get('call_id')) is str and r['call_id'] for r in all_calls))
    require(len({r['call_id'] for r in all_calls}) == len(all_calls))
    require(all(type(r.get('used')) is int and r['used'] == n
                for n, r in enumerate(all_calls, 1)))
    inputs = [i for i, r in enumerate(trace) if r.get('event') == 'dispatch' and r.get('tool') == 'type_text']
    require(len(inputs) == 1)
    paired, consumed, last = [], set(), None
    for index, call in calls:
        key = call['call_id']
        rows = [(i, r) for i, r in enumerate(trace) if r.get('call_id') == key]
        require([r.get('event') for _, r in rows] == ['dispatch', 'helper_arguments', 'result'])
        require(all(r.get('run_id') == run_id and r.get('tool') == 'check_draft' for _, r in rows))
        require(index == rows[0][0] < rows[1][0] < rows[2][0] < inputs[0])
        consumed.update(i for i, _ in rows)
        args, response = rows[1][1].get('args'), rows[2][1].get('value')
        require(type(args) is dict and set(args) == {'raw'} and type(args['raw']) is str)
        require(0 < len(args['raw'].encode()) <= 65536)
        independently = check_draft(submission, args['raw'], run_id=run_id, session_id=session_id)
        require(type(response) is dict and response.get('status') == independently['status'])
        require(response.get('inputSha256') == digest and type(response.get('used')) is int
                and response['used'] == call['used'])
        require(response.get('semanticVerified') is False and response.get('guiVerified') is False)
        if independently['status'] == 'DRAFT_STRUCTURE_VALID':
            expected = {k: independently[k] for k in ('status', 'semanticVerified', 'guiVerified',
                'rawSha256', 'canonicalJson', 'document', 'documentSha256')}
            expected.update(inputSha256=digest, used=call['used'])
            require(canonical(response) == canonical(expected))
            last = independently
        else:
            # Independent refusal, not an assertion that guest reason taxonomy
            # was recomputed. Full guest trace protocol remains a separate gate.
            require(set(response) <= {'status', 'code', 'semanticVerified', 'guiVerified',
                                      'inputSha256', 'used', 'line', 'column'})
            require(type(response.get('code')) is str and 0 < len(response['code']) <= 64)
            for field in ('line', 'column'):
                if field in response:
                    require(type(response[field]) is int and 0 < response[field] <= 65537)
            last = None
        paired.append((args, response))
    require(consumed == {i for i, _ in draft_rows})
    require(last is not None and type(document) is bytes)
    require(canonical(report).decode() == last['canonicalJson'] and document == last['document'].encode())
    official_calls = [(i, r) for i, r in enumerate(official)
                      if r.get('type') == 'tool/call' and r.get('data', {}).get('name') == 'vm_check_draft']
    require(len(official_calls) == len(paired))
    ids, previous = set(), -1
    for (index, call), (args, response) in zip(official_calls, paired):
        data = call['data']; key = data.get('callId')
        require(type(key) is str and bool(key) and key not in ids); ids.add(key)
        matching_calls = [r for r in official if r.get('type') == 'tool/call'
                          and r.get('data', {}).get('callId') == key]
        results = [(i, r) for i, r in enumerate(official) if r.get('type') == 'tool/result'
                   and r.get('data', {}).get('message', {}).get('toolCallId') == key]
        require(len(matching_calls) == 1 and len(results) == 1)
        end, result = results[0]
        require(previous < index < end); previous = end
        require(type(call.get('seq')) is int and type(result.get('seq')) is int
                and call['seq'] < result['seq'])
        require(type(data.get('arguments')) is str and canonical(strict_json(data['arguments'])) == canonical(args))
        message = result['data']['message']
        require(message.get('isError', False) is False)
        content = message.get('content')
        require(type(content) is list and len(content) == 1 and type(content[0]) is dict
                and set(content[0]) == {'type', 'text'} and content[0]['type'] == 'text'
                and type(content[0]['text']) is str)
        require(canonical(strict_json(content[0]['text'])) == canonical(response))
    if draft_input_mode == 'checked-draft-v1':
        verify_checked_input(trace, official, run_id=run_id, document=document,
                             input_at=inputs[0], draft_end=previous)
    return dict(status='DRAFT_EVIDENCE_MATCHED', calls=len(calls),
                canonicalSha256=hashlib.sha256(last['canonicalJson'].encode()).hexdigest(),
                documentSha256=last['documentSha256'], semanticVerified=False, guiVerified=False,
                **({'inputMode': draft_input_mode} if draft_input_mode == 'checked-draft-v1' else {}))


def verify_checked_input(trace, official, *, run_id, document, input_at, draft_end):
    """Host comparison against independently projected bytes, not a GUI verifier."""
    selections = [(i, r) for i, r in enumerate(trace) if r.get('event') == 'checked_draft_input_intent']
    require(len(selections) == 1)
    index, selection = selections[0]
    require(set(selection) == {'event','run_id','at','mode','args','used','resolvedText'}
            and selection['run_id'] == run_id and selection['mode'] == 'checked-draft-v1'
            and selection['resolvedText'] == document.decode() and index + 1 == input_at)
    call = trace[input_at]
    require(type(selection['used']) is int and selection['used'] == call['used'] - 1)
    args = selection['args']
    require(type(args) is dict and set(args) == {'snapshot_id','element_index','element_token','documentSha256'}
            and type(args['element_index']) is int and args['element_index'] >= 0
            and type(args['snapshot_id']) is str and bool(args['snapshot_id'])
            and type(args['element_token']) is str and bool(args['element_token'])
            and args['documentSha256'] == hashlib.sha256(document).hexdigest())
    results = [(i, r) for i, r in enumerate(trace) if r.get('call_id') == call['call_id']]
    require([r.get('event') for _, r in results] == ['dispatch','result'])
    require(all(r.get('run_id') == run_id and r.get('tool') == 'type_text' for _, r in results))
    result_at, result = results[-1]
    require(input_at < result_at and type(result.get('value')) is dict)
    value = result['value']
    require(value.get('status') not in ('refused','error','failed') and 'error' not in value
            and value.get('effect') != 'refused' and value.get('isError') is not True)
    attempts = [(i, r) for i, r in enumerate(trace) if r.get('event') == 'attempted_input']
    require(len(attempts) == 1)
    attempt_at, attempt = attempts[0]
    require(result_at < attempt_at and attempt.get('run_id') == run_id
            and attempt.get('snapshot_id') == args['snapshot_id']
            and type(attempt.get('element_index')) is int and attempt['element_index'] == args['element_index']
            and type(attempt.get('bytes')) is int and attempt['bytes'] == len(document)
            and attempt.get('sha256') == args['documentSha256'])
    calls = [(i, r) for i, r in enumerate(official) if r.get('type') == 'tool/call']
    require(not any(r.get('data', {}).get('name') == 'vm_type' for _, r in calls))
    inputs = [(i, r) for i, r in calls if r.get('data', {}).get('name') == 'vm_type_checked_draft']
    require(len(inputs) == 1)
    start, chosen = inputs[0]; data = chosen['data']; key = data.get('callId')
    require(draft_end < start and type(key) is str and bool(key)
            and sum(r.get('data', {}).get('callId') == key for _, r in calls) == 1)
    require(type(data.get('arguments')) is str and canonical(strict_json(data['arguments'])) == canonical(args))
    responses = [(i, r) for i, r in enumerate(official) if r.get('type') == 'tool/result'
                 and r.get('data', {}).get('message', {}).get('toolCallId') == key]
    require(len(responses) == 1)
    end, response = responses[0]
    require(start < end and type(chosen.get('seq')) is int and type(response.get('seq')) is int
            and chosen['seq'] < response['seq'])
    message = response['data']['message']; content = message.get('content')
    require(message.get('isError', False) is False and type(content) is list and len(content) == 1
            and type(content[0]) is dict and set(content[0]) == {'type','text'}
            and content[0]['type'] == 'text' and type(content[0]['text']) is str)
    require(canonical(strict_json(content[0]['text'])) == canonical(value))
