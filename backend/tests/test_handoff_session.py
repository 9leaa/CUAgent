import copy
import json
import pytest
from backend.handoff_session import extract_handoff_result, MODEL, TOOLS
from backend.tests.test_handoff_result import fixture, RUN, SESSION


def evidence():
    source, report = fixture()
    prompt = dict(sessionId=SESSION, requestId='original-request', mode='queue',
                  content=[dict(type='text', text='original frozen prompt')])
    def assistant(identity, content):
        return dict(type='assistant/message', data=dict(turn=1, step=1, message=dict(id=identity,
            role='assistant', source=dict(kind='model', provider=MODEL['provider'], model=MODEL['model']), content=content)))
    rows = [dict(type='session', version=4, id=SESSION, cwd='/private/run/workspace',
                 agentPreset='project-handoff', isSeeded=False, delegationDepth=0),
        dict(type='turn/start', data=dict(turn=1)),
        dict(type='user/message', data=dict(role='user', source=dict(kind='user', rpcId=prompt['requestId']), content=prompt['content'])),
        dict(type='request/header', data=dict(header=dict(config=MODEL.copy(), tools=[dict(name=t) for t in sorted(TOOLS)]))),
        assistant('intermediate', [dict(type='tool-call', id='call-1', name='vm_read_materials', arguments='{}')]),
        dict(type='tool/call', data=dict(callId='call-1', name='vm_read_materials', arguments='{}')),
        dict(type='tool/result', data=dict(message=dict(toolCallId='call-1', isError=False, content=[]))),
        assistant('final', [dict(type='text', text=json.dumps(report, ensure_ascii=False))]),
        dict(type='turn/end', data=dict(turn=1, reason=dict(kind='completed')))]
    for index, row in enumerate(rows[1:]): row['seq'] = index
    return source, prompt, rows


def extract(source, prompt, rows):
    raw = '\n'.join(json.dumps(r, ensure_ascii=False) for r in rows).encode()
    return extract_handoff_result(raw, submission=source, run_id=RUN, session_id=SESSION,
        cwd='/private/run/workspace', prompt=prompt)


def test_original_message_extracted_without_claiming_full_session_or_semantics():
    source, prompt, rows = evidence(); original = copy.deepcopy(rows)
    result = extract(source, prompt, rows)
    assert result['status'] == 'SESSION_RESULT_EXTRACTED'
    assert result['messageId'] == 'final'
    assert result['document'].startswith('项目:'.encode())
    assert result['report']['inputSha256'] == fixture()[1]['inputSha256']
    assert all(result[k] is False for k in ('sessionVerified', 'guiVerified', 'semanticVerified'))
    assert original == rows


@pytest.mark.parametrize('fault', ['session', 'cwd', 'preset', 'seed', 'delegation', 'seq', 'second-turn',
    'incomplete', 'rpc', 'prompt', 'provider', 'thinking', 'extra-tool', 'call-id', 'call-name',
    'call-args', 'result-id', 'error', 'final-source', 'final-before-tools', 'duplicate-message'])
def test_provenance_policy_and_order_rejected(fault):
    source, prompt, rows = evidence()
    if fault == 'session': rows[0]['id'] = 'other'
    elif fault == 'cwd': rows[0]['cwd'] = '/other'
    elif fault == 'preset': rows[0]['agentPreset'] = 'real-app'
    elif fault == 'seed': rows[0]['isSeeded'] = True
    elif fault == 'delegation': rows[0]['delegationDepth'] = True
    elif fault == 'seq': rows[3]['seq'] = rows[2]['seq']
    elif fault == 'second-turn': rows.append(dict(type='turn/start', seq=99, data=dict(turn=2)))
    elif fault == 'incomplete': rows[-1]['data']['reason']['kind'] = 'aborted'
    elif fault == 'rpc': rows[2]['data']['source']['rpcId'] = 'other'
    elif fault == 'prompt': rows[2]['data']['content'] = [dict(type='text', text='different')]
    elif fault == 'provider': rows[3]['data']['header']['config']['provider'] = 'other'
    elif fault == 'thinking': rows[3]['data']['header']['config']['reasoningEffort'] = 'high'
    elif fault == 'extra-tool': rows[3]['data']['header']['tools'].append(dict(name='shell'))
    elif fault == 'call-id': rows[5]['data']['callId'] = 'other'
    elif fault == 'call-name': rows[5]['data']['name'] = 'shell'
    elif fault == 'call-args': rows[5]['data']['arguments'] = '{"path":"/other"}'
    elif fault == 'result-id': rows[6]['data']['message']['toolCallId'] = 'other'
    elif fault == 'error': rows[6]['data']['message']['isError'] = True
    elif fault == 'final-source': rows[7]['data']['message']['source']['kind'] = 'user'
    elif fault == 'final-before-tools': rows[6], rows[7] = rows[7], rows[6]; rows[6]['seq'], rows[7]['seq'] = 5, 6
    else: rows[7]['data']['message']['id'] = 'intermediate'
    with pytest.raises(ValueError): extract(source, prompt, rows)


@pytest.mark.parametrize('fault', ['fence', 'prefix', 'suffix', 'duplicate', 'nan', 'array', 'image', 'oversize', 'wrong-fact', 'wrong-source'])
def test_final_result_is_strict_json_and_independently_checked(fault):
    source, prompt, rows = evidence()
    message = rows[7]['data']['message']; text = message['content'][0]['text']
    if fault == 'fence': text = '```json\n' + text + '\n```'
    elif fault == 'prefix': text = 'Here is the result: ' + text
    elif fault == 'suffix': text += '{}'
    elif fault == 'duplicate': text = '{"kind":"project-handoff",' + text[1:]
    elif fault == 'nan': text = '{"a":NaN}'
    elif fault == 'array': text = '[' + text + ']'
    elif fault == 'image': message['content'].append(dict(type='image')); text = text
    elif fault == 'oversize': text += ' ' * 65536
    else:
        report = json.loads(text)
        if fault == 'wrong-fact': report['tasks'][0]['owner'] = 'invented'
        else: report['tasks'][0]['progress']['citations'][0]['quote'] = 'fabricated'
        text = json.dumps(report)
    message['content'][0]['text'] = text
    with pytest.raises(ValueError): extract(source, prompt, rows)


def test_never_extracts_report_from_tool_return_or_stream():
    source, prompt, rows = evidence()
    final = rows[7]['data']['message']['content'][0]['text']
    rows[6]['data']['message']['content'] = [dict(type='text', text=final)]
    rows[7]['data']['stream'] = [dict(text=final)]
    rows[7]['data']['message']['content'][0]['text'] = 'No final report'
    with pytest.raises(ValueError): extract(source, prompt, rows)
