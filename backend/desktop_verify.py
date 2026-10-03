"""Independent session-policy checks; GUI acceptance remains a separate gate."""
import hashlib
import json
import os
from backend.desktop_collect import private_path
from backend.desktop_contract import DesktopSubmission
from backend.desktop_session import MODEL

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
    users = [row for row in rows if row['type'] == 'user/message']
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
            require(data['name'] == 'vm_write_result')
            errors.append(call)
        parsed.append((data['name'], json.loads(data['arguments']), message))
    require(len(errors) == sum(row['event'] == 'dispatch' and row.get('tool') == 'rejected_write_result' for row in trace))
    typed = [args for name, args, _ in parsed if name == 'vm_type']
    expected = submission.expected_document()
    require(len(typed) == 1 and typed[0].get('text', '').encode() == expected)
    inputs = [row for row in trace if row['event'] == 'attempted_input']
    require(len(inputs) == 1 and inputs[0]['snapshot_id'] == typed[0]['snapshot_id']
            and inputs[0]['sha256'] == hashlib.sha256(expected).hexdigest())
    require([args['snapshot_id'] for name, args, _ in parsed if name == 'vm_save'] ==
            [row['snapshot_id'] for row in trace if row['event'] == 'attempted_save'])
    observations = [message for name, _, message in parsed if name == 'vm_observe']
    require(bool(observations) and all(any(block.get('type') == 'image' for block in message['content']) for message in observations))
    reads = [message for name, _, message in parsed if name == 'vm_read_result']
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
            'model': MODEL.copy(), 'officialToolCalls': len(calls), 'rawCalls': guest_bundle['guest']['rawCalls']}
