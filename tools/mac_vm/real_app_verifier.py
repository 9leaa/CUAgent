"""Read-only independent acceptance. No Task construction or desktop operations."""
import hashlib
from real_app_bridge import body_from_state


def verify_evidence(rows, expected, document, result, fresh_state):
    dispatched = [row for row in rows if row['event'] == 'dispatch']
    returned = [row for row in rows if row['event'] in ('result', 'error')]
    inputs = [row for row in rows if row['event'] == 'attempted_input']
    saves = [row for row in rows if row['event'] == 'attempted_save']
    states = [row for row in returned if row['event'] == 'result' and row.get('tool') == 'get_window_state']
    calls = {row['call_id']: row for row in dispatched}
    native = body_from_state(fresh_state).encode('utf8')
    permitted = {'launch_app', 'list_windows', 'get_window_state', 'type_text', 'hotkey',
                 'bring_to_front', 'write_result', 'read_result', 'rejected_write_result'}
    complete = (len(dispatched) <= 30 and len(calls) == len(dispatched) == len(returned)
                and {row['call_id'] for row in returned} == set(calls)
                and [row['used'] for row in dispatched] == list(range(1, len(dispatched) + 1))
                and all(row.get('tool') in permitted for row in dispatched)
                and not any(row['event'] == 'UNKNOWN' or (row['event'] == 'error' and row.get('tool') != 'get_window_state') for row in rows))
    grounded = True
    for attempt in inputs + saves:
        sources = [row for row in states if row['value'].get('snapshot_id') == attempt['snapshot_id']]
        if len(sources) != 1:
            grounded = False
            continue
        source = sources[0]
        tool = 'type_text' if attempt['event'] == 'attempted_input' else 'hotkey'
        prior = [row for row in dispatched if row['tool'] == tool and source['at'] <= row['at'] <= attempt['at']]
        grounded &= (len(prior) == 1 and 0 <= prior[0]['at'] - source['at'] <= 30
                     and source['value'].get('screenshot_frame_valid') is True
                     and source['value'].get('pid') == fresh_state.get('pid')
                     and source['value'].get('window_id') == fresh_state.get('window_id'))
        if tool == 'hotkey':
            displayed = body_from_state(source['value']).encode('utf8')
            grounded &= expected in (displayed, displayed + b'\n')
    passed = (complete and grounded and len(inputs) == 1 and len(saves) >= 1
              and len([row for row in dispatched if row['tool'] == 'type_text']) == 1
              and len([row for row in dispatched if row['tool'] == 'hotkey']) == len(saves)
              and inputs[0]['at'] < min(row['at'] for row in saves)
              and inputs[0]['sha256'] == hashlib.sha256(expected).hexdigest()
              and document == expected and result == expected + b'\n'
              and expected in (native, native + b'\n')
              and fresh_state.get('screenshot_frame_valid') is True
              and any(row.get('tool') == 'read_result' and row.get('value') == result.decode('utf8') for row in returned))
    return {'status': 'SUCCEEDED' if passed else 'UNVERIFIED', 'raw_calls': len(dispatched),
            'inputs': len(inputs), 'saves': len(saves), 'fresh_display': native.decode('utf8'),
            'document_bytes': len(document), 'document_sha256': hashlib.sha256(document).hexdigest(),
            'rejected_calls': sum(row['tool'].startswith('rejected_') for row in dispatched),
            'rule': 'all attempts retained; Save may repeat only after a new grounded observation; no edit replay'}
