"""P6 official notice classification. Does not edit or omit session evidence.

Shared templates/thresholds are DeepSeek MIT; see THIRD_PARTY_NOTICES.md.
"""
import json
import math
from pathlib import Path

POLICY = json.loads((Path(__file__).resolve().parents[1] / 'agent/harness/desktop-notices.json').read_text())


def require(value):
    if not value:
        raise ValueError('UNVERIFIED_FRAMEWORK_NOTICE')


def canonical(value):
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        # JSON.stringify enumerates integer-index keys before other sorted keys.
        keys = sorted(value)
        indices = [key for key in keys if key.isascii() and key.isdecimal()
                   and str(int(key)) == key and int(key) < 4294967295]
        ordered = sorted(indices, key=int) + [key for key in keys if key not in indices]
        return {key: canonical(value[key]) for key in ordered}
    if type(value) is float and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def reminder_text(name, count, arguments_text):
    if count == POLICY['thresholds'][0]:
        return POLICY['gentle']
    # JavaScript String.length/slice measure UTF-16 code units, not code points.
    raw = arguments_text.encode('utf-16-le', errors='surrogatepass')
    size, cap = len(raw) // 2, POLICY['previewChars']
    preview = (raw[:cap * 2].decode('utf-16-le', errors='surrogatepass') + f'… (+{size - cap} more chars)'
               if size > cap else arguments_text)
    return POLICY['detailed'].replace('{tool}', name).replace('{count}', str(count)).replace('{arguments}', preview)


def classify_desktop_messages(rows):
    users = [row for row in rows if row['type'] == 'user/message']
    prompts = [row for row in users if row.get('data', {}).get('source', {}).get('kind') == 'user']
    notices = [row for row in users if row.get('data', {}).get('source', {}).get('kind') != 'user']
    if not notices:
        return prompts, 0
    events = [row for row in rows if row['type'] != 'session']
    require(all(type(row.get('seq')) is int and (index == 0 or row['seq'] > events[index - 1]['seq'])
                for index, row in enumerate(events)))
    calls, completed, pending = {}, set(), []
    chain, count, accepted = None, 0, 0
    for row in events:
        if row['type'] == 'tool/call':
            data = row['data']
            require(isinstance(data.get('callId'), str) and data['callId'] not in calls
                    and isinstance(data.get('name'), str) and isinstance(data.get('arguments'), str))
            def reject_constant(_):
                raise ValueError('non-JSON constant')
            try:
                args = json.loads(data['arguments'], parse_constant=reject_constant)
            except ValueError:
                args = data['arguments']
            calls[data['callId']] = (data['name'], json.dumps(canonical(args), ensure_ascii=False, separators=(',', ':')))
        elif row['type'] == 'tool/result':
            identity = row['data']['message']['toolCallId']
            require(identity in calls and identity not in completed)
            completed.add(identity)
            name, text = calls[identity]
            count = count + 1 if chain == (name, text) else 1
            chain = name, text
            if name in POLICY['tools'] and count in POLICY['thresholds']:
                pending.append({'source': {'kind': POLICY['sourceKind'], 'form': POLICY['form'],
                    'summary': f'{name} × {count}'}, 'content': [{'type': 'text', 'text': reminder_text(name, count, text)}]})
        elif row['type'] == 'user/message':
            data = row['data']
            if data.get('source', {}).get('kind') == 'user':
                chain, count, pending = None, 0, []
                continue
            require(bool(pending))
            expected = pending.pop(0)
            require(data.get('role') == 'user' and data.get('source') == expected['source']
                    and data.get('content') == expected['content'])
            accepted += 1
    require(accepted == len(notices))
    return prompts, accepted
