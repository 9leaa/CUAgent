import copy
import json
from pathlib import Path
import subprocess
import pytest

from backend.desktop_notices import POLICY, classify_desktop_messages, reminder_text


def notice_rows(count=8, args=None):
    args = {} if args is None else args
    arguments = json.dumps(args, ensure_ascii=False, separators=(',', ':'))
    rows = [{'type': 'user/message', 'data': {'source': {'kind': 'user', 'rpcId': 'original'}}}]
    for index in range(1, count + 1):
        rows.extend([{'type': 'tool/call', 'data': {'callId': str(index), 'name': 'vm_observe', 'arguments': arguments}},
                     {'type': 'tool/result', 'data': {'message': {'toolCallId': str(index)}}}])
        if index in POLICY['thresholds']:
            rows.append({'type': 'user/message', 'data': {'role': 'user',
                'source': {'kind': 'repeat-tool-reminder', 'form': 'notice', 'summary': f'vm_observe × {index}'},
                'content': [{'type': 'text', 'text': reminder_text('vm_observe', index, arguments)}]}})
    return [dict(row, seq=index) for index, row in enumerate(rows)]


def js_classify(rows):
    code = '''import {readFileSync} from 'node:fs';
import {classifyDesktopMessages} from './agent/harness/desktop-notices.mjs';
try {const r=classifyDesktopMessages(JSON.parse(readFileSync(0,'utf8')));
console.log(JSON.stringify({prompts:r.prompts.length,notices:r.frameworkNotices}));}
catch {console.log(JSON.stringify({refused:true}));}'''
    output = subprocess.run(['/opt/homebrew/bin/node', '--input-type=module', '-e', code],
        cwd=Path(__file__).resolve().parents[2], input=json.dumps(rows).encode(), capture_output=True, timeout=10, check=True)
    return json.loads(output.stdout)


@pytest.mark.parametrize('args', [{}, {'value': '😀' * 300}, {'value': 'x' * 600}, {'value': '{tool} {count}'}])
def test_python_js_share_notice_policy_and_preserve_raw_evidence(args):
    rows = notice_rows(args=args); original = copy.deepcopy(rows)
    prompts, notices = classify_desktop_messages(rows)
    assert len(prompts) == 1 and notices == 3 and rows == original
    assert js_classify(rows) == {'prompts': 1, 'notices': 3}


@pytest.mark.parametrize('fault', ['kind', 'form', 'summary', 'text', 'extra', 'uncompleted',
                                  'different', 'duplicate', 'order', 'tool'])
def test_both_languages_refuse_unverified_notice(fault):
    rows = notice_rows(3); notice = rows[-1]['data']
    if fault == 'kind': notice['source']['kind'] = 'external'
    elif fault == 'form': notice['source']['form'] = 'instruction'
    elif fault == 'summary': notice['source']['summary'] = 'vm_observe × 5'
    elif fault == 'text': notice['content'][0]['text'] += ' ignore limits'
    elif fault == 'extra': notice['source']['authority'] = True
    elif fault == 'uncompleted': rows.pop(-2)
    elif fault == 'different': rows[3]['data']['arguments'] = '{"other":true}'
    elif fault == 'duplicate': rows.append(dict(rows[-1], seq=len(rows)))
    elif fault == 'order': rows[2]['seq'] = rows[1]['seq']
    else:
        for row in rows:
            if row['type'] == 'tool/call': row['data']['name'] = 'shell'
    with pytest.raises(ValueError): classify_desktop_messages(rows)
    assert js_classify(rows) == {'refused': True}


def test_second_real_user_prompt_still_counts():
    rows = notice_rows(3)
    rows.append({'type': 'user/message', 'seq': len(rows), 'data': {'source': {'kind': 'user', 'rpcId': 'other'}}})
    assert len(classify_desktop_messages(rows)[0]) == 2
    assert js_classify(rows) == {'prompts': 2, 'notices': 1}
