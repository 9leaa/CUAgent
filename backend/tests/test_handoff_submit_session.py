import copy
import hashlib
import json

import pytest
from backend.handoff_document import expected_document
from backend.handoff_result import canonical, input_digest
from backend.handoff_session import extract_handoff_result
from backend.tests.test_handoff_session import evidence
from backend.tests.test_handoff_result import RUN, SESSION


def submitted():
    source, prompt, rows = evidence()
    report = json.loads(rows[7]['data']['message']['content'][0]['text'])
    document = expected_document(source, report, run_id=RUN, session_id=SESSION)
    arguments = json.dumps({'report': report}, ensure_ascii=False)
    rows[3]['data']['header']['tools'].append({'name': 'vm_submit_handoff'})
    rows[7]['data']['message']['content'] = [dict(type='text', text='Submitting the report.'),
        dict(type='tool-call', id='submit-1', name='vm_submit_handoff', arguments=arguments)]
    response = dict(status='HANDOFF_SUBMITTED', protocol='p7-tool-submit-v1',
        reportSha256=hashlib.sha256(canonical(report)).hexdigest(),
        documentSha256=hashlib.sha256(document).hexdigest(), semanticVerified=False, guiVerified=False,
        inputSha256=input_digest(source), runId=RUN, sessionId=SESSION, used=17)
    rows[-1:-1] = [dict(type='tool/call', data=dict(callId='submit-1', name='vm_submit_handoff', arguments=arguments)),
        dict(type='tool/result', data=dict(message=dict(toolCallId='submit-1', isError=False,
            content=[dict(type='text', text=json.dumps(response))])))]
    return source, prompt, rows


def extract(source, prompt, rows, protocol='p7-tool-submit-v1'):
    for i, row in enumerate(rows[1:]): row['seq'] = i
    return extract_handoff_result(b'\n'.join(canonical(r) for r in rows), submission=source,
        run_id=RUN, session_id=SESSION, cwd='/private/run/workspace', prompt=prompt, protocol=protocol)


def test_complete_original_model_tool_arguments_not_plain_text_or_return():
    source, prompt, rows = submitted()
    result = extract(source, prompt, rows)
    assert result['protocol'] == 'p7-tool-submit-v1' and result['submissionCallId'] == 'submit-1'
    assert result['messageId'] == 'final' and result['officialToolCalls'] == 2
    assert not any(result[k] for k in ('sessionVerified', 'guiVerified', 'semanticVerified'))


@pytest.mark.parametrize('mode', ['legacy', 'unknown', 'missing_tool', 'missing_submit', 'wrong_source',
    'args_changed', 'duplicate_key', 'raw_report', 'extra_args', 'result_changed', 'error', 'budget',
    'boolean_budget', 'missing_result', 'after_assistant', 'after_request', 'extra_call'])
def test_explicit_protocol_provenance_and_terminal_result(mode):
    source, prompt, rows = submitted()
    protocol = 'p7-tool-submit-v1'
    if mode == 'legacy': protocol = 'legacy-final-json'
    if mode == 'unknown': protocol = 'auto'
    if mode == 'missing_tool': rows[3]['data']['header']['tools'].pop()
    if mode == 'missing_submit': rows[7:10] = []
    if mode == 'wrong_source': rows[7]['data']['message']['source']['kind'] = 'user'
    if mode == 'args_changed': rows[8]['data']['arguments'] = '{}'
    if mode in ('duplicate_key', 'raw_report', 'extra_args'):
        old = rows[8]['data']['arguments']
        if mode == 'duplicate_key': new = '{"report":{},' + old[1:]
        elif mode == 'raw_report': new = json.dumps({'report': old})
        else: new = json.dumps(dict(json.loads(old), sessionId=SESSION))
        rows[8]['data']['arguments'] = rows[7]['data']['message']['content'][-1]['arguments'] = new
    if mode == 'error': rows[9]['data']['message']['isError'] = True
    if mode in ('result_changed', 'budget', 'boolean_budget'):
        content = rows[9]['data']['message']['content'][0]
        response = json.loads(content['text'])
        if mode == 'result_changed': response['reportSha256'] = '0' * 64
        else: response['used'] = True if mode == 'boolean_budget' else 31
        content['text'] = json.dumps(response)
    if mode == 'missing_result': rows.pop(9)
    if mode == 'after_assistant':
        row = copy.deepcopy(rows[7]); row['data']['message']['id'] = 'later'
        row['data']['message']['content'] = [dict(type='text', text='Done')]
        rows.insert(-1, row)
    if mode == 'after_request': rows.insert(-1, copy.deepcopy(rows[3]))
    if mode == 'extra_call':
        rows[7]['data']['message']['content'].append(dict(type='tool-call', id='later', name='vm_read_result', arguments='{}'))
        rows[-1:-1] = [dict(type='tool/call', data=dict(callId='later', name='vm_read_result', arguments='{}')),
            dict(type='tool/result', data=dict(message=dict(toolCallId='later', isError=False, content=[])))]
    with pytest.raises(ValueError): extract(source, prompt, rows, protocol)


def test_no_auto_upgrade_old_strict_final_json():
    source, prompt, rows = evidence()
    with pytest.raises(ValueError): extract(source, prompt, rows)
    assert extract(source, prompt, rows, 'legacy-final-json')['status'] == 'SESSION_RESULT_EXTRACTED'
