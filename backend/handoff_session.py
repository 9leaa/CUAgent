"""Extract the original final report; full two-log session acceptance is separate."""
import hashlib
import json

from backend.desktop_notices import classify_desktop_messages
from backend.desktop_session import MODEL
from backend.handoff_document import expected_document
from backend.handoff_result import HandoffResult, verify_result, canonical, input_digest

TOOLS = {'vm_check_draft', 'vm_locate_quote', 'vm_observe', 'vm_read_materials', 'vm_read_result', 'vm_reopen', 'vm_save', 'vm_type', 'vm_write_result'}


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_SESSION_RESULT_UNVERIFIED')


def handoff_tools(protocol='legacy-final-json', draft_input_mode='literal-text'):
    require(protocol in ('legacy-final-json', 'p7-tool-submit-v1')
            and draft_input_mode in ('literal-text', 'checked-draft-v1')
            and (draft_input_mode == 'literal-text' or protocol == 'p7-tool-submit-v1'))
    tools = TOOLS | {'vm_submit_handoff'} if protocol == 'p7-tool-submit-v1' else set(TOOLS)
    if draft_input_mode == 'checked-draft-v1':
        tools = (tools - {'vm_type'}) | {'vm_type_checked_draft'}
    return tools


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    def constant(_):
        raise ValueError('HANDOFF_SESSION_RESULT_UNVERIFIED')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def extract_handoff_result(raw, *, submission, run_id, session_id, cwd, prompt,
                           protocol='legacy-final-json', draft_input_mode='literal-text'):
    """No file writes/RPC. Trusted caller must bind prompt/cwd to original intent.

    This does NOT authenticate arbitrary supplied logs or prove GUI execution.
    The full verifier must additionally compare the original request audit and
    each official tool exchange against the independently collected VM trace.
    """
    require(protocol in ('legacy-final-json', 'p7-tool-submit-v1'))
    structured = protocol == 'p7-tool-submit-v1'
    allowed_tools = handoff_tools(protocol, draft_input_mode)
    require(type(raw) is bytes and 0 < len(raw) <= 64 * 1024 * 1024)
    rows = [strict_json(line) for line in raw.decode('utf8').splitlines()]
    require(len(rows) > 1 and all(type(row) is dict for row in rows))
    header, events = rows[0], rows[1:]
    require(header.get('type') == 'session' and type(header.get('version')) is int and header['version'] == 4
            and header.get('id') == session_id and header.get('cwd') == cwd and 'seq' not in header
            and header.get('agentPreset') == 'project-handoff' and header.get('isSeeded') is False
            and type(header.get('delegationDepth')) is int and header['delegationDepth'] == 0)
    require(all(type(r.get('seq')) is int and r['seq'] >= 0 and r.get('type') != 'session' for r in events))
    require([r['seq'] for r in events] == sorted({r['seq'] for r in events}))
    def selected(kind): return [r for r in events if r['type'] == kind]
    starts, ends = selected('turn/start'), selected('turn/end')
    require(len(starts) == len(ends) == 1 and starts[0]['seq'] < ends[0]['seq'])
    require(type(starts[0]['data'].get('turn')) is int and starts[0]['data']['turn'] == 1
            and type(ends[0]['data'].get('turn')) is int and ends[0]['data']['turn'] == 1
            and ends[0]['data'].get('reason') == {'kind': 'completed'})
    users, notices = classify_desktop_messages(events)
    require(len(users) == 1 and type(prompt) is dict and prompt.get('sessionId') == session_id
            and type(prompt.get('requestId')) is str and bool(prompt['requestId']) and prompt.get('mode') == 'queue')
    user = users[0]
    require(starts[0]['seq'] < user['seq'] < ends[0]['seq'] and user['data'].get('role') == 'user'
            and user['data'].get('source') == {'kind': 'user', 'rpcId': prompt['requestId']}
            and user['data'].get('content') == prompt.get('content') and bool(prompt.get('content')))
    requests = selected('request/header')
    require(bool(requests))
    for request in requests:
        config = request['data']['header']
        require(all(config['config'].get(k) == v for k, v in MODEL.items())
                and sorted(t['name'] for t in config['tools']) == sorted(allowed_tools)
                and user['seq'] < request['seq'] < ends[0]['seq'])
    assistants = selected('assistant/message')
    require(bool(assistants) and requests[0]['seq'] < assistants[0]['seq'])
    declared = {}
    ids = set()
    for row in assistants:
        data, message = row['data'], row['data']['message']
        require(type(data.get('turn')) is int and data['turn'] == 1
                and user['seq'] < row['seq'] < ends[0]['seq'] and message.get('role') == 'assistant'
                and type(message.get('id')) is str and bool(message['id']) and message['id'] not in ids)
        ids.add(message['id'])
        source = message.get('source', {})
        require(source.get('kind') == 'model' and all(source.get(k) == MODEL[k] for k in ('provider', 'model')))
        require(type(message.get('content')) is list and bool(message['content']))
        for block in message['content']:
            require(type(block) is dict)
            if block.get('type') != 'tool-call': continue
            key = block.get('id')
            require(type(key) is str and bool(key) and key not in declared and block.get('name') in allowed_tools
                    and type(block.get('arguments')) is str and type(strict_json(block['arguments'])) is dict)
            declared[key] = (row['seq'], block)
    calls, results = selected('tool/call'), selected('tool/result')
    require(0 < len(calls) == len(results) == len(declared) <= 30)
    pending, complete = set(), set()
    for row in events:
        if row['type'] == 'tool/call':
            data = row['data']; key = data.get('callId')
            require(type(key) is str and key in declared and key not in pending and key not in complete)
            seq, block = declared[key]
            require(seq < row['seq'] < ends[0]['seq'] and data.get('name') == block['name']
                    and data.get('arguments') == block['arguments'])
            pending.add(key)
        elif row['type'] == 'tool/result':
            message = row['data']['message']; key = message.get('toolCallId')
            require(type(key) is str and key in pending and row['seq'] < ends[0]['seq']
                    and message.get('isError', False) is False)
            pending.remove(key); complete.add(key)
    require(not pending and complete == set(declared))
    final = assistants[-1]
    submitted_response = None
    if structured:
        submissions = [(key, seq, block) for key, (seq, block) in declared.items()
                       if block['name'] == 'vm_submit_handoff']
        require(len(submissions) == 1)
        key, seq, block = submissions[0]
        require(seq == final['seq'] and calls[-1]['data']['callId'] == key
                and results[-1]['data']['message']['toolCallId'] == key
                and requests[-1]['seq'] < seq)
        require(list(declared)[-1] == key)
        text = block['arguments']
        require(0 < len(text.encode('utf8')) <= 64 * 1024)
        envelope = strict_json(text)
        require(type(envelope) is dict and set(envelope) == {'report'} and type(envelope['report']) is dict)
        report = HandoffResult.model_validate(envelope['report'])
        content = results[-1]['data']['message'].get('content')
        require(type(content) is list and len(content) == 1 and type(content[0]) is dict
                and set(content[0]) == {'type', 'text'} and content[0]['type'] == 'text'
                and type(content[0]['text']) is str and 0 < len(content[0]['text'].encode()) <= 4096)
        submitted_response = strict_json(content[0]['text'])
    else:
        require(final['seq'] > max(r['seq'] for r in results))
        content = final['data']['message']['content']
        require(all(set(b) == {'type', 'text'} and b['type'] == 'text' and type(b['text']) is str for b in content))
        text = ''.join(b['text'] for b in content)
        require(0 < len(text.encode('utf8')) <= 64 * 1024)
        report = HandoffResult.model_validate(strict_json(text))
    structure = verify_result(submission, report, run_id=run_id, session_id=session_id)
    document = expected_document(submission, report, run_id=run_id, session_id=session_id)
    if structured:
        require(type(submitted_response) is dict)
        used = submitted_response.get('used')
        require(type(used) is int and len(calls) <= used <= 30)
        expected_response = dict(status='HANDOFF_SUBMITTED', protocol=protocol,
            reportSha256=hashlib.sha256(canonical(report.model_dump())).hexdigest(),
            documentSha256=hashlib.sha256(document).hexdigest(), semanticVerified=False, guiVerified=False,
            inputSha256=input_digest(submission), runId=run_id, sessionId=session_id, used=used)
        require(canonical(submitted_response) == canonical(expected_response))
    return {'status': 'SESSION_RESULT_EXTRACTED', 'report': report.model_dump(), 'document': document,
            'structure': structure, 'sessionSha256': hashlib.sha256(raw).hexdigest(),
            'messageSha256': hashlib.sha256(text.encode('utf8')).hexdigest(),
            'messageId': final['data']['message']['id'], 'messageSeq': final['seq'],
            'officialToolCalls': len(calls), 'frameworkNotices': notices,
            **({'protocol': protocol, 'submissionCallId': key} if structured else {}),
            **({'inputMode': draft_input_mode} if draft_input_mode == 'checked-draft-v1' else {}),
            'sessionVerified': False, 'guiVerified': False, 'semanticVerified': False}
