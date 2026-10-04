import hashlib
import json
import pytest
from backend.desktop_contract import DesktopSubmission
from backend.desktop_verify import verify_desktop_session, MODEL, TOOLS


@pytest.fixture
def evidence(tmp_path):
    root = tmp_path / 'run'
    root.mkdir(mode=0o700)
    submission = DesktopSubmission(kind='desktop-textedit', lines=['交接'])
    expected = submission.expected_document()
    rows = [{'type': 'user/message', 'data': {'source': {'kind': 'user', 'rpcId': 'request'}}},
            {'type': 'request/header', 'data': {'header': {'config': MODEL.copy(), 'tools': [{'name': name} for name in sorted(TOOLS)]}}}]
    specs = [('vm_observe', {}, [{'type': 'image'}]),
             ('vm_type', {'snapshot_id': 'a', 'text': expected.decode()}, []),
             ('vm_observe', {}, [{'type': 'image'}]), ('vm_save', {'snapshot_id': 'b'}, []),
             ('vm_observe', {}, [{'type': 'image'}]), ('vm_write_result', {'value': expected.decode()}, []),
             ('vm_read_result', {}, [{'type': 'text', 'text': json.dumps({'content': (expected + b'\n').decode()})}])]
    for index, (name, args, content) in enumerate(specs):
        rows.extend([{'type': 'tool/call', 'data': {'callId': str(index), 'name': name, 'arguments': json.dumps(args)}},
                     {'type': 'tool/result', 'data': {'message': {'toolCallId': str(index), 'isError': False, 'content': content}}}])
    rows.append({'type': 'turn/end', 'data': {'reason': {'kind': 'completed'}}})
    for index, row in enumerate(rows): row['seq'] = index
    trace = [{'event': 'dispatch', 'tool': 'type_text', 'call_id': 'type'},
             {'event': 'result', 'tool': 'type_text', 'call_id': 'type', 'value': {}},
             {'event': 'attempted_input', 'snapshot_id': 'a', 'sha256': hashlib.sha256(expected).hexdigest()},
             {'event': 'attempted_save', 'snapshot_id': 'b'},
             {'event': 'dispatch', 'tool': 'write_result', 'call_id': 'write'},
             {'event': 'result', 'tool': 'write_result', 'call_id': 'write', 'value': expected.decode()},
             {'event': 'dispatch', 'tool': 'read_result', 'call_id': 'read'},
             {'event': 'result', 'tool': 'read_result', 'call_id': 'read', 'value': (expected + b'\n').decode()}]
    bundle = {'binding': {'runId': 'run'}, 'guest': {'vmStatus': 'VERIFIED', 'rawCalls': 12},
              'files': {'trace.jsonl': b'\n'.join(json.dumps(row).encode() for row in trace)}}
    files = {'desktop-session-binding.json': {'runId': 'run', 'sessionId': 'session', 'cwd': str(root / 'workspace'), 'lines': ['交接']},
             'prompt-request.json': {'request': {'sessionId': 'session', 'requestId': 'request'}}}
    for name, value in files.items():
        (root / name).write_text(json.dumps(value))
        (root / name).chmod(0o600)
    audit = [{'provider': MODEL['provider'], 'model': MODEL['model'], 'toolNames': sorted(TOOLS), 'imageBlocks': 1}]
    return root, submission, bundle, rows, audit


def verify(evidence):
    root, submission, bundle, rows, audit = evidence
    for name, values in [('session.jsonl', rows), ('request-audit.jsonl', audit)]:
        (root / name).write_text(''.join(json.dumps(row) + '\n' for row in values))
        (root / name).chmod(0o600)
    return verify_desktop_session(root, session_id='session', submission=submission, guest_bundle=bundle)


def test_synthetic_session_policy_and_guest_correlation(evidence):
    result = verify(evidence)
    assert result['sessionVerified'] is True
    assert result['officialToolCalls'] == 7 and result['rawCalls'] == 12
    assert 'status' not in result


@pytest.mark.parametrize('fault', [None, 'official-success', 'guest-not-refused', 'guest-error',
    'missing-result', 'duplicate-result', 'no-observe', 'late-refusal', 'extra-type', 'missing-guest'])
def test_input_refusal_requires_ordered_guest_proof_and_fresh_observe(evidence, fault):
    _, _, bundle, rows, _ = evidence
    trace = [json.loads(line) for line in bundle['files']['trace.jsonl'].splitlines()]
    original = next(row for row in rows if row['type'] == 'tool/call' and row['data']['name'] == 'vm_type')
    call = {'type': 'tool/call', 'data': {**original['data'], 'callId': 'refused'}}
    result = {'type': 'tool/result', 'data': {'message': {'toolCallId': 'refused', 'isError': True,
              'content': [{'type': 'text', 'text': 'Error: DESKTOP_REQUEST_REJECTED'}]}}}
    observe = [{'type': 'tool/call', 'data': {'callId': 'fresh', 'name': 'vm_observe', 'arguments': '{}'}},
               {'type': 'tool/result', 'data': {'message': {'toolCallId': 'fresh', 'content': [{'type': 'image'}]}}}]
    index = rows.index(original)
    rows[index:index] = [call, result, *observe]
    pair = [{'event': 'dispatch', 'tool': 'rejected_type_text', 'call_id': 'refused'},
            {'event': 'result', 'tool': 'rejected_type_text', 'call_id': 'refused',
             'value': {'status': 'refused', 'reason': 'DESKTOP_REQUEST_REJECTED'}}]
    trace[:0] = pair
    if fault == 'official-success': result['data']['message']['isError'] = False
    if fault == 'guest-not-refused': pair[1]['value']['status'] = 'ok'
    if fault == 'guest-error': pair[1]['event'] = 'error'
    if fault == 'missing-result': trace.remove(pair[1])
    if fault == 'duplicate-result': trace.insert(2, dict(pair[1]))
    if fault == 'no-observe':
        for row in observe: rows.remove(row)
    if fault == 'late-refusal':
        trace.remove(pair[0]); trace.remove(pair[1]); trace.extend(pair)
    if fault == 'extra-type':
        trace[2:2] = [{'event': 'dispatch', 'tool': 'type_text', 'call_id': 'extra'},
                      {'event': 'result', 'tool': 'type_text', 'call_id': 'extra', 'value': {}}]
    if fault == 'missing-guest':
        trace.remove(pair[0]); trace.remove(pair[1])
    for index, row in enumerate(rows): row['seq'] = index
    bundle['files']['trace.jsonl'] = b'\n'.join(json.dumps(row).encode() for row in trace)
    if fault is None: assert verify(evidence)['recoveredInputRefusals'] == 1
    else:
        with pytest.raises(ValueError): verify(evidence)


@pytest.mark.parametrize('fault', [None, 'wrong-error', 'guest-success', 'official-success', 'late-error',
                                 'missing-guest', 'duplicate-result', 'missing-final', 'extra-official'])
def test_read_failure_requires_matching_original_guest_order_and_late_readback(evidence, fault):
    _, _, bundle, rows, _ = evidence
    trace = [json.loads(line) for line in bundle['files']['trace.jsonl'].splitlines()]
    call = {'type': 'tool/call', 'data': {'callId': 'probe', 'name': 'vm_read_result', 'arguments': '{}'}}
    result = {'type': 'tool/result', 'data': {'message': {'toolCallId': 'probe', 'isError': True,
               'content': [{'type': 'text', 'text': 'Error: DESKTOP_REQUEST_REJECTED'}]}}}
    index = next(i for i, row in enumerate(rows) if row['type'] == 'tool/call' and row['data']['name'] == 'vm_write_result')
    rows[index:index] = [call, result]
    early = [{'event': 'dispatch', 'tool': 'read_result', 'call_id': 'probe'},
             {'event': 'error', 'tool': 'read_result', 'call_id': 'probe', 'error': 'FileNotFoundError'}]
    trace[2:2] = early
    if fault == 'wrong-error': early[1]['error'] = 'PermissionError'
    if fault == 'guest-success': early[1]['event'] = 'result'
    if fault == 'official-success': result['data']['message']['isError'] = False
    if fault == 'late-error':
        trace.remove(early[0]); trace.remove(early[1]); trace.extend(early)
    if fault == 'missing-guest': trace.remove(early[1])
    if fault == 'duplicate-result': trace.insert(4, dict(early[1]))
    if fault == 'missing-final':
        trace[:] = trace[:-2]
        rows[:] = [row for row in rows if not (row.get('type') == 'tool/call' and row['data']['callId'] == '6')
                   and not (row.get('type') == 'tool/result' and row['data']['message']['toolCallId'] == '6')]
    if fault == 'extra-official':
        rows[index:index] = [{'type': 'tool/call', 'data': {**call['data'], 'callId': 'extra'}},
                            {'type': 'tool/result', 'data': {'message': {**result['data']['message'], 'toolCallId': 'extra'}}}]
    for index, row in enumerate(rows): row['seq'] = index
    bundle['files']['trace.jsonl'] = b'\n'.join(json.dumps(row).encode() for row in trace)
    if fault is None:
        assert verify(evidence)['recoveredMissingReads'] == 1
    else:
        with pytest.raises(ValueError): verify(evidence)


@pytest.mark.parametrize('fault', [None, 'id', 'cwd', 'version', 'duplicate'])
def test_official_metadata_requires_original_identity(evidence, fault):
    root, _, _, rows, _ = evidence
    header = {'type': 'session', 'id': 'session', 'version': 4, 'cwd': str(root / 'workspace')}
    if fault in ('id', 'cwd', 'version'): header[fault] = 'wrong'
    rows.insert(0, header)
    if fault == 'duplicate': rows.insert(0, header.copy())
    if fault is None:
        assert verify(evidence)['sessionVerified'] is True
    else:
        with pytest.raises(ValueError): verify(evidence)


@pytest.mark.parametrize('mutation', ['model', 'tools', 'prompt', 'terminal', 'duplicate', 'missing',
                                     'input', 'snapshot', 'readback', 'image', 'audit', 'error'])
def test_policy_or_correlation_failure_never_passes(evidence, mutation):
    _, _, _, rows, audit = evidence
    if mutation == 'model': rows[1]['data']['header']['config']['reasoningEffort'] = 'high'
    elif mutation == 'tools': rows[1]['data']['header']['tools'].append({'name': 'shell'})
    elif mutation == 'prompt': rows[0]['data']['source']['rpcId'] = 'other'
    elif mutation == 'terminal': rows[-1]['data']['reason']['kind'] = 'aborted'
    elif mutation == 'duplicate': rows.insert(1, rows[0].copy())
    elif mutation == 'missing': rows.pop(3)
    elif mutation == 'input': rows[4]['data']['arguments'] = json.dumps({'snapshot_id': 'a', 'text': 'wrong'})
    elif mutation == 'snapshot': rows[8]['data']['arguments'] = json.dumps({'snapshot_id': 'other'})
    elif mutation == 'readback': rows[-2]['data']['message']['content'] = [{'type': 'text', 'text': '{"content":"wrong"}'}]
    elif mutation == 'image': rows[3]['data']['message']['content'] = []
    elif mutation == 'audit': audit[0]['imageBlocks'] = 0
    else: rows[5]['data']['message']['isError'] = True
    with pytest.raises(ValueError): verify(evidence)


@pytest.mark.parametrize('second_prompt', [False, True])
def test_verified_notice_is_reported_but_second_user_prompt_is_still_rejected(evidence, second_prompt):
    from backend.desktop_notices import POLICY
    rows = evidence[3]
    extra = []
    for index in range(3):
        identity = 'notice-observe-' + str(index)
        extra.extend([{'type': 'tool/call', 'data': {'callId': identity, 'name': 'vm_observe', 'arguments': '{}'}},
            {'type': 'tool/result', 'data': {'message': {'toolCallId': identity, 'content': [{'type': 'image'}]}}}])
    extra.append({'type': 'user/message', 'data': {'role': 'user',
        'source': {'kind': 'repeat-tool-reminder', 'form': 'notice', 'summary': 'vm_observe × 3'},
        'content': [{'type': 'text', 'text': POLICY['gentle']}]}})
    if second_prompt:
        extra.append({'type': 'user/message', 'data': {'source': {'kind': 'user', 'rpcId': 'other'}}})
    rows[-1:-1] = extra
    for index, row in enumerate(rows): row['seq'] = index
    if second_prompt:
        with pytest.raises(ValueError): verify(evidence)
    else:
        result = verify(evidence)
        assert result['sessionVerified'] and result['frameworkNotices'] == 1
