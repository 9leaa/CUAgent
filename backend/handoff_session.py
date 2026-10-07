"""Extract the original final report; full two-log session acceptance is separate."""
import hashlib
import json

from backend.desktop_notices import classify_desktop_messages
from backend.desktop_session import MODEL
from backend.handoff_document import expected_document
from backend.handoff_result import HandoffResult, verify_result

TOOLS = {'vm_locate_quote', 'vm_observe', 'vm_read_materials', 'vm_read_result', 'vm_reopen', 'vm_save', 'vm_type', 'vm_write_result'}


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_SESSION_RESULT_UNVERIFIED')


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


def extract_handoff_result(raw, *, submission, run_id, session_id, cwd, prompt):
    """No file writes/RPC. Trusted caller must bind prompt/cwd to original intent.

    This does NOT authenticate arbitrary supplied logs or prove GUI execution.
    The full verifier must additionally compare the original request audit and
    each official tool exchange against the independently collected VM trace.
    """
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
                and sorted(t['name'] for t in config['tools']) == sorted(TOOLS)
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
            require(type(key) is str and bool(key) and key not in declared and block.get('name') in TOOLS
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
    require(final['seq'] > max(r['seq'] for r in results))
    content = final['data']['message']['content']
    require(all(set(b) == {'type', 'text'} and b['type'] == 'text' and type(b['text']) is str for b in content))
    text = ''.join(b['text'] for b in content)
    require(0 < len(text.encode('utf8')) <= 64 * 1024)
    report = HandoffResult.model_validate(strict_json(text))
    structure = verify_result(submission, report, run_id=run_id, session_id=session_id)
    document = expected_document(submission, report, run_id=run_id, session_id=session_id)
    return {'status': 'SESSION_RESULT_EXTRACTED', 'report': report.model_dump(), 'document': document,
            'structure': structure, 'sessionSha256': hashlib.sha256(raw).hexdigest(),
            'messageSha256': hashlib.sha256(text.encode('utf8')).hexdigest(),
            'messageId': final['data']['message']['id'], 'messageSeq': final['seq'],
            'officialToolCalls': len(calls), 'frameworkNotices': notices,
            'sessionVerified': False, 'guiVerified': False, 'semanticVerified': False}
