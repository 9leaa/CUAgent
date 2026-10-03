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
    trace = [{'event': 'attempted_input', 'snapshot_id': 'a', 'sha256': hashlib.sha256(expected).hexdigest()},
             {'event': 'attempted_save', 'snapshot_id': 'b'}]
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
