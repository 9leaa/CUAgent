"""Independent session-policy checks; GUI acceptance remains a separate gate."""
import hashlib
import json
import os
from backend.desktop_collect import private_path
from backend.desktop_contract import DesktopSubmission
from backend.desktop_session import MODEL
from backend.desktop_notices import classify_desktop_messages

TOOLS = {'vm_observe', 'vm_type', 'vm_save', 'vm_write_result', 'vm_read_result'}


def require(value):
    if not value:
        raise ValueError('DESKTOP_SESSION_EVIDENCE_UNVERIFIED')


def verify_desktop_session(root, *, session_id, submission, guest_bundle):
    root = private_path(root, directory=True)
    require(isinstance(submission, DesktopSubmission))
    require(guest_bundle['binding']['runId'] == root.name and guest_bundle['guest']['vmStatus'] == 'VERIFIED')
    def read(name, limit):
        path = private_path(root / name, directory=False)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as file:
            raw = file.read(limit + 1)
        require(len(raw) <= limit)
        return raw
    binding = json.loads(read('desktop-session-binding.json', 32768))
    require(binding == {'runId': root.name, 'sessionId': session_id, 'cwd': str(root / 'workspace'),
                        'lines': list(submission.lines)})
    prompt = json.loads(read('prompt-request.json', 32768))['request']
    require(prompt['sessionId'] == session_id and isinstance(prompt['requestId'], str) and bool(prompt['requestId']))
    raw = read('session.jsonl', 64 * 1024 * 1024)
    rows = [json.loads(line) for line in raw.splitlines()]
    if rows and rows[0].get('type') == 'session':
        header = rows.pop(0)
        require(header.get('version') == 4 and header.get('id') == session_id
                and header.get('cwd') == binding['cwd'] and 'seq' not in header)
    require(bool(rows) and all(type(row.get('seq')) is int for row in rows))
    require([row['seq'] for row in rows] == sorted({row['seq'] for row in rows}))
    users, framework_notices = classify_desktop_messages(rows)
    ends = [row for row in rows if row['type'] == 'turn/end']
    require(len(users) == len(ends) == 1 and ends[0]['data']['reason']['kind'] == 'completed')
    require(users[0]['data']['source'].get('kind') == 'user'
            and users[0]['data']['source'].get('rpcId') == prompt['requestId'])
    headers = [row['data']['header'] for row in rows if row['type'] == 'request/header']
    require(bool(headers))
    for header in headers:
        require(all(header['config'].get(key) == value for key, value in MODEL.items()))
        require(sorted(tool['name'] for tool in header['tools']) == sorted(TOOLS))
    trace = [json.loads(line) for line in guest_bundle['files']['trace.jsonl'].splitlines()]
    calls = [row for row in rows if row['type'] == 'tool/call']
    results = [row for row in rows if row['type'] == 'tool/result']
    require(0 < len(calls) == len(results) <= 30)
    require(len({row['data']['callId'] for row in calls}) == len(calls))
    parsed, errors = [], []
    for call in calls:
        data = call['data']
        require(data['name'] in TOOLS and users[0]['seq'] < call['seq'] < ends[0]['seq'])
        matches = [row for row in results if row['data']['message']['toolCallId'] == data['callId']]
        require(len(matches) == 1 and call['seq'] < matches[0]['seq'] < ends[0]['seq'])
        message = matches[0]['data']['message']
        require(type(message.get('isError', False)) is bool)
        if message.get('isError'):
            require(data['name'] in ('vm_write_result', 'vm_read_result', 'vm_type'))
            if data['name'] == 'vm_write_result': errors.append(call)
        parsed.append((data['name'], json.loads(data['arguments']), message))
    require(len(errors) == sum(row['event'] == 'dispatch' and row.get('tool') == 'rejected_write_result' for row in trace))
    guest_inputs = [row for row in trace if row['event'] == 'dispatch'
                    and row.get('tool') in ('type_text', 'rejected_type_text')]
    official_inputs = [(index, args, message) for index, (name, args, message) in enumerate(parsed) if name == 'vm_type']
    require(len(guest_inputs) == len(official_inputs) and bool(guest_inputs))
    typed, input_refusals = [], 0
    for call, (index, args, message) in zip(guest_inputs, official_inputs):
        matches = [row for row in trace if row['event'] in ('result', 'error')
                   and row.get('call_id') == call.get('call_id')]
        require(len(matches) == 1 and matches[0].get('tool') == call['tool']
                and matches[0]['event'] == 'result' and trace.index(call) < trace.index(matches[0]))
        if call['tool'] == 'rejected_type_text':
            require(message.get('isError') is True and not typed
                    and matches[0].get('value') == {'status': 'refused', 'reason': 'DESKTOP_REQUEST_REJECTED'})
            input_refusals += 1
        else:
            require(message.get('isError', False) is False)
            if input_refusals:
                last_refused = max(i for i, _, m in official_inputs if i < index and m.get('isError') is True)
                require(any(name == 'vm_observe' for name, _, _ in parsed[last_refused + 1:index]))
            typed.append(args)
    expected = submission.expected_document()
    require(len(typed) == 1 and typed[0].get('text', '').encode() == expected)
    inputs = [row for row in trace if row['event'] == 'attempted_input']
    require(len(inputs) == 1 and inputs[0]['snapshot_id'] == typed[0]['snapshot_id']
            and inputs[0]['sha256'] == hashlib.sha256(expected).hexdigest())
    require([args['snapshot_id'] for name, args, _ in parsed if name == 'vm_save'] ==
            [row['snapshot_id'] for row in trace if row['event'] == 'attempted_save'])
    observations = [message for name, _, message in parsed if name == 'vm_observe']
    require(bool(observations) and all(any(block.get('type') == 'image' for block in message['content']) for message in observations))
    # Match ordered reads/writes across the two independent logs; guest call
    # IDs differ from official IDs, so counts alone cannot establish ordering.
    names = {'read_result': 'vm_read_result', 'write_result': 'vm_write_result',
             'rejected_write_result': 'vm_write_result'}
    guest_io = [row for row in trace if row['event'] == 'dispatch' and row.get('tool') in names]
    official_io = [(name, message) for name, _, message in parsed if name in names.values()]
    require([names[row['tool']] for row in guest_io] == [name for name, _ in official_io])
    writes = [index for index, row in enumerate(guest_io) if row['tool'] == 'write_result']
    require(len(writes) == 1)
    reads, recovered = [], 0
    for index, (call, (name, message)) in enumerate(zip(guest_io, official_io)):
        if name != 'vm_read_result': continue
        matches = [row for row in trace if row['event'] in ('result', 'error') and row.get('call_id') == call.get('call_id')]
        require(len(matches) == 1 and matches[0].get('tool') == 'read_result'
                and trace.index(call) < trace.index(matches[0]))
        result = matches[0]
        if message.get('isError', False):
            require(index < writes[0] and result['event'] == 'error' and result.get('error') == 'FileNotFoundError')
            recovered += 1
            continue
        require(index > writes[0] and result['event'] == 'result'
                and result.get('value') == (expected + b'\n').decode())
        reads.append(message)
    require(bool(reads))
    for message in reads:
        texts = [json.loads(block['text']) for block in message['content'] if block.get('type') == 'text']
        require(any(isinstance(value, dict) and value.get('content') == (expected + b'\n').decode() for value in texts))
    audit = [json.loads(line) for line in read('request-audit.jsonl', 8 * 1024 * 1024).splitlines()]
    require(bool(audit))
    for row in audit:
        require(row.get('provider') == MODEL['provider'] and row.get('model') == MODEL['model']
                and sorted(row['toolNames']) == sorted(TOOLS) and type(row.get('imageBlocks')) is int and row['imageBlocks'] >= 0)
    require(any(row['imageBlocks'] > 0 for row in audit))
    return {'sessionVerified': True, 'sessionId': session_id, 'sessionSha256': hashlib.sha256(raw).hexdigest(),
            'model': MODEL.copy(), 'officialToolCalls': len(calls), 'rawCalls': guest_bundle['guest']['rawCalls'],
            'frameworkNotices': framework_notices, 'recoveredMissingReads': recovered,
            'recoveredInputRefusals': input_refusals}
