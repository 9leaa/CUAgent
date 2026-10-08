"""Independent structured-submit gate; full session/GUI/transport gates remain required."""
import hashlib

from backend.handoff_draft import check_draft
from backend.handoff_draft_evidence import verify_draft_evidence
from backend.handoff_result import canonical, input_digest
from backend.handoff_session import strict_json


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_SUBMISSION_EVIDENCE_UNVERIFIED')


def verify_submission_evidence(trace, official, *, submission, run_id, session_id,
                               binding, document):
    require(type(trace) is list and 0 < len(trace) <= 512 and type(official) is list)
    selected = [(i, r) for i, r in enumerate(trace) if r.get('tool') == 'submit_handoff']
    require([r.get('event') for _, r in selected] == ['dispatch', 'helper_arguments', 'result'])
    (start, call), (_, arguments), (end, result) = selected
    key = call.get('call_id')
    require(type(key) is str and bool(key))
    require(all(r.get('run_id') == run_id and r.get('call_id') == key for _, r in selected))
    require([(i, r) for i, r in enumerate(trace) if r.get('call_id') == key] == selected)
    require(not any(r.get('event') in ('stop', 'error') for r in trace[:end + 1]))
    calls = [(i, r) for i, r in enumerate(trace) if r.get('event') == 'dispatch']
    require(2 <= len(calls) <= 30 and calls[-1][0] == start)
    require(all(type(r.get('used')) is int and r['used'] == n for n, (_, r) in enumerate(calls, 1)))
    previous_at, previous = calls[-2]
    require(previous.get('tool') == 'read_result')
    reads = [(i, r) for i, r in enumerate(trace) if r.get('event') == 'result'
             and r.get('call_id') == previous.get('call_id')]
    require(len(reads) == 1 and previous_at < reads[0][0] < start)
    require(type(document) is bytes and reads[0][1].get('value') == document.decode() + '\n')
    args = arguments.get('args')
    require(type(args) is dict and set(args) == {'report'} and type(args['report']) is dict)
    raw = canonical(args['report'])
    require(0 < len(raw) <= 65536)
    checked = check_draft(submission, raw.decode(), run_id=run_id, session_id=session_id)
    require(checked['status'] == 'DRAFT_STRUCTURE_VALID' and checked['document'].encode() == document)
    draft = verify_draft_evidence(trace, official, submission=submission, run_id=run_id,
        session_id=session_id, binding=binding, report=args['report'], document=document)
    response = dict(status='HANDOFF_SUBMITTED', protocol='p7-tool-submit-v1',
                    reportSha256=hashlib.sha256(checked['canonicalJson'].encode()).hexdigest(),
                    documentSha256=checked['documentSha256'], semanticVerified=False, guiVerified=False,
                    inputSha256=input_digest(submission), runId=run_id, sessionId=session_id, used=len(calls))
    require(canonical(result.get('value')) == canonical(response))
    tool_calls = [(i, r) for i, r in enumerate(official) if r.get('type') == 'tool/call']
    submits = [(i, r) for i, r in tool_calls if r.get('data', {}).get('name') == 'vm_submit_handoff']
    require(len(submits) == 1 and tool_calls[-1] == submits[0])
    index, official_call = submits[0]
    data = official_call['data']; call_id = data.get('callId')
    require(type(call_id) is str and bool(call_id))
    require(sum(r.get('data', {}).get('callId') == call_id for _, r in tool_calls) == 1)
    finishes = [(i, r) for i, r in enumerate(official) if r.get('type') == 'tool/result'
                and r.get('data', {}).get('message', {}).get('toolCallId') == call_id]
    require(len(finishes) == 1 and finishes[0][0] > index)
    finish = finishes[0][1]
    require(type(official_call.get('seq')) is int and type(finish.get('seq')) is int
            and official_call['seq'] < finish['seq'])
    require(type(data.get('arguments')) is str and canonical(strict_json(data['arguments'])) == canonical(args))
    message = finish['data']['message']
    require(message.get('isError', False) is False)
    content = message.get('content')
    require(type(content) is list and len(content) == 1 and type(content[0]) is dict
            and set(content[0]) == {'type', 'text'} and content[0]['type'] == 'text'
            and type(content[0]['text']) is str)
    require(canonical(strict_json(content[0]['text'])) == canonical(response))
    return dict(status='SUBMISSION_EVIDENCE_MATCHED', protocol='p7-tool-submit-v1',
                report=args['report'], reportSha256=response['reportSha256'],
                documentSha256=response['documentSha256'], draft=draft,
                rawCalls=len(calls), sessionVerified=False, guiVerified=False, semanticVerified=False)
