"""Pure P7 trace checks; not file, official-session, or semantic acceptance.

Input must come from trusted frozen evidence collection, never a model bundle.
This first validator deliberately rejects failed/rejected calls. It preserves
them as unverified evidence rather than erasing them to manufacture a pass.
"""
import hashlib
import json
import math
import re

from real_app_bridge import body_from_state
from handoff_task import close_target


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_TRACE_UNVERIFIED')


def verify_handoff_trace(rows, *, run_id, materials, expected):
    require(isinstance(run_id, str) and re.fullmatch(
        r'p2-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', run_id))
    require(type(materials) is bytes and 0 < len(materials) <= 256 * 1024)
    require(type(expected) is bytes and 0 < len(expected) <= 4096)
    source = json.loads(materials)
    require(type(source) is dict and source.get('kind') == 'project-handoff')
    require(json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False).encode('utf8') == materials)
    digest = hashlib.sha256(expected).hexdigest()
    input_digest = hashlib.sha256(materials).hexdigest()
    expected_text = expected.decode('utf8')
    require(type(rows) is list and 0 < len(rows) <= 512)
    tools = {'launch_app', 'list_windows', 'get_window_state', 'type_text', 'hotkey', 'click',
             'bring_to_front', 'read_materials', 'reopen_document', 'write_result', 'read_result'}
    events = {'approval', 'setup_empty_document', 'dispatch', 'result', 'observation_evidence', 'attempted_input',
              'attempted_save', 'handoff_reopen_intent', 'handoff_window_closed',
              'handoff_window_reopened', 'stop', 'window_readiness_wait', 'observation_recovery'}
    calls, returned, by_event = {}, {}, {}
    stopped, last = False, -math.inf
    for index, row in enumerate(rows):
        require(type(row) is dict and row.get('run_id') == run_id and row.get('event') in events)
        at = row.get('at')
        require(type(at) in (int, float) and math.isfinite(at) and at >= last)
        last = at
        event = row['event']
        by_event.setdefault(event, []).append(index)
        if event == 'stop': stopped = True
        if event == 'dispatch':
            key = row.get('call_id')
            require(not stopped and type(key) is str and bool(key) and key not in calls)
            require(len(calls) == len(returned) and row.get('tool') in tools)
            require(type(row.get('used')) is int and row['used'] == len(calls) + 1 <= 30)
            calls[key] = index
        elif event == 'result':
            key = row.get('call_id')
            require(type(key) is str and key in calls and key not in returned)
            require(rows[calls[key]]['tool'] == row.get('tool'))
            returned[key] = index
    require(bool(calls) and calls.keys() == returned.keys())

    def tool_calls(tool):
        return [i for i in calls.values() if rows[i]['tool'] == tool]

    def value(index):
        return rows[returned[rows[index]['call_id']]].get('value')

    def between(start, end):
        return [i for i in calls.values() if start < i < end]

    def one(event):
        indices = by_event.get(event, [])
        require(len(indices) == 1)
        return indices[0]

    approval = one('approval')
    setup = one('setup_empty_document')
    require(approval < setup < min(calls.values()) and rows[approval].get('allowed_app') == 'com.apple.TextEdit'
            and rows[approval].get('case_id') == 'real_textedit')
    require(rows[setup].get('bytes') == 0 and rows[setup].get('sha256') == hashlib.sha256(b'').hexdigest())
    for call in calls.values():
        if rows[call]['tool'] in {'write_result', 'read_result', 'read_materials', 'reopen_document'}:
            continue
        result = value(call)
        require(type(result) is dict and result.get('status') not in ('refused', 'error', 'failed')
                and result.get('effect') != 'refused' and 'error' not in result and result.get('isError') is not True
                and result.get('code') not in ('delivery_failed', 'foreground_unavailable', 'background_unavailable', 'permission_denied'))

    observations = {}
    observed_calls = set()
    by_used = {rows[i]['used']: i for i in calls.values()}
    for index in by_event.get('observation_evidence', []):
        row = rows[index]
        used = row.get('used')
        require(type(used) is int and used in by_used)
        call = by_used[used]
        require(call not in observed_calls and rows[call]['tool'] == 'get_window_state')
        require(returned[rows[call]['call_id']] < index and not between(call, index))
        state = value(call)
        require(type(state) is dict and state.get('screenshot_frame_valid') is True and not state.get('degraded_reason'))
        snapshot = state.get('snapshot_id')
        require(type(snapshot) is str and bool(snapshot) and snapshot == row.get('snapshot_id')
                and snapshot not in observations)
        require(type(state.get('pid')) is int and state['pid'] > 0
                and type(state.get('window_id')) is int and state['window_id'] > 0)
        require(state.get('app_name') == 'TextEdit' and state.get('window_title') == 'handoff-' + run_id + '.txt')
        observations[snapshot] = (index, state, call)
        observed_calls.add(call)
    require(observed_calls == set(tool_calls('get_window_state')) and bool(observations))

    def fresh(snapshot, target):
        require(type(snapshot) is str and snapshot in observations)
        index, state, call = observations[snapshot]
        require(index < target and not between(index, target))
        require(0 <= rows[target]['at'] - rows[returned[rows[call]['call_id']]]['at'] <= 30)
        return state

    def body(state):
        displayed = body_from_state(state).encode('utf8')
        require(expected in (displayed, displayed + b'\n'))

    intent_at, closed_at, opened_at = (one(e) for e in (
        'handoff_reopen_intent', 'handoff_window_closed', 'handoff_window_reopened'))
    require(intent_at < closed_at < opened_at)
    intent, closed, opened = (rows[i] for i in (intent_at, closed_at, opened_at))
    for row, fields in ((intent, ('pid', 'window_id')), (closed, ('pid', 'window_id')),
                        (opened, ('pid', 'window_id', 'old_window_id'))):
        require(all(type(row.get(field)) is int and row[field] > 0 for field in fields))
    before = fresh(intent.get('snapshot_id'), intent_at)
    pid, old = before['pid'], before['window_id']
    require(intent.get('pid') == pid and intent.get('window_id') == old and intent.get('sha256') == digest)
    body(before)
    try:
        button = close_target(before)
    except Exception as error:
        raise ValueError('HANDOFF_TRACE_UNVERIFIED') from error
    require(all(intent.get(key) == item for key, item in button.items()))
    require(sum(i < intent_at for i in calls.values()) <= 19)
    require(closed.get('pid') == pid and closed.get('window_id') == old)
    require(opened.get('pid') == pid and opened.get('old_window_id') == old and opened.get('sha256') == digest)
    new = opened.get('window_id')
    require(type(new) is int and new > 0)
    require(type(opened.get('used')) is int and opened['used'] == sum(i < opened_at for i in calls.values()))

    def inventory(index):
        response = value(index)
        require(type(response) is dict and type(response.get('windows')) is list)
        windows = response['windows']
        for window in windows:
            require(type(window) is dict and type(window.get('pid')) is int
                    and type(window.get('window_id')) is int and window['window_id'] > 0
                    and type(window.get('is_on_screen')) is bool
                    and type(window.get('title')) is str and type(window.get('app_name')) is str)
        return windows

    closing = between(intent_at, closed_at)
    opening = between(closed_at, opened_at)
    require(2 <= len(closing) <= 4 and 2 <= len(opening) <= 4)
    require([rows[i]['tool'] for i in closing] == ['click'] + ['list_windows'] * (len(closing) - 1))
    require(tool_calls('click') == [closing[0]])
    require([rows[i]['tool'] for i in opening] == ['reopen_document'] + ['list_windows'] * (len(opening) - 1))
    require(tool_calls('reopen_document') == [opening[0]])
    title = 'handoff-' + run_id + '.txt'
    for position, call in enumerate(closing[1:]):
        present = any(w['pid'] == pid and (w['window_id'] == old or w['title'] == title) for w in inventory(call))
        require(present == (position < len(closing) - 2))
    require(value(opening[0]) == {'requested': True, 'pid': pid, 'documentSha256': digest})
    for position, call in enumerate(opening[1:]):
        matches = [w for w in inventory(call) if w['pid'] == pid and w['title'] == title
                   and w['app_name'] == 'TextEdit' and w['is_on_screen']]
        require((not matches) if position < len(opening) - 2 else (len(matches) == 1 and matches[0]['window_id'] == new))
    require(returned[rows[closing[-1]]['call_id']] < closed_at
            and returned[rows[opening[-1]]['call_id']] < opened_at)

    input_at = one('attempted_input')
    inputs = tool_calls('type_text')
    saves = by_event.get('attempted_save', [])
    require(len(inputs) == 1 and bool(saves) and input_at < min(saves) <= max(saves) < intent_at)
    require(rows[input_at].get('sha256') == digest and type(rows[input_at].get('bytes')) is int
            and rows[input_at]['bytes'] == len(expected))
    save_calls = []
    for index in [input_at] + saves:
        attempt = rows[index]
        require(attempt.get('snapshot_id') in observations)
        start = observations[attempt['snapshot_id']][0]
        candidates = between(start, index)
        require(len(candidates) == 1)
        call = candidates[0]
        require(rows[call]['tool'] == ('type_text' if index == input_at else 'hotkey'))
        require(returned[rows[call]['call_id']] < index)
        state = fresh(attempt['snapshot_id'], call)
        require((state['pid'], state['window_id']) == (pid, old))
        if index != input_at:
            body(state)
            save_calls.append(call)
    require(tool_calls('hotkey') == save_calls)
    material_calls = tool_calls('read_materials')
    require(bool(material_calls) and min(material_calls) < inputs[0])
    for call in material_calls:
        require(json.dumps(value(call), ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                           allow_nan=False).encode('utf8') == materials
                and rows[returned[rows[call]['call_id']]].get('inputSha256') == input_digest)
    launches = tool_calls('launch_app')
    require(len(launches) == 1 and launches[0] < inputs[0])
    require(type(value(launches[0])) is dict and value(launches[0]).get('pid') == pid
            and value(launches[0]).get('bundle_id') == 'com.apple.TextEdit')
    for index, state, _ in observations.values():
        require(index < intent_at or index > opened_at)
        require((state['pid'], state['window_id']) == (pid, old if index < intent_at else new))
        if index > opened_at: body(state)
    writes, reads = tool_calls('write_result'), tool_calls('read_result')
    require(len(writes) == 1 and bool(reads) and opened_at < writes[0] < min(reads))
    latest = max(observations, key=lambda s: observations[s][0] if observations[s][0] < writes[0] else -1)
    require(observations[latest][0] > opened_at)
    body(fresh(latest, writes[0]))
    require(value(writes[0]) == expected_text)
    require(all(value(i) == expected_text + '\n' for i in reads))
    require(all(rows[i]['tool'] in {'get_window_state', 'write_result', 'read_result', 'read_materials'}
                for i in calls.values() if i > opened_at))
    return {'status': 'TRACE_VERIFIED', 'runId': run_id, 'rawCalls': len(calls),
            'inputSha256': input_digest, 'documentSha256': digest, 'finalSnapshotId': latest,
            'filesVerified': False, 'sessionVerified': False, 'semanticVerified': False}
