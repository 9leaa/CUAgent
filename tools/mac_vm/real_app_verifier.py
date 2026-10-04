"""Read-only independent acceptance. No Task construction or desktop operations."""
import hashlib
from real_app_bridge import body_from_state


def verify_evidence(rows, expected, document, result, fresh_state, *, allow_missing_result_read=False,
                    allow_rejected_input=False):
    dispatched = [row for row in rows if row['event'] == 'dispatch']
    returned = [row for row in rows if row['event'] in ('result', 'error')]
    inputs = [row for row in rows if row['event'] == 'attempted_input']
    saves = [row for row in rows if row['event'] == 'attempted_save']
    states = [row for row in returned if row['event'] == 'result' and row.get('tool') == 'get_window_state']
    calls = {row['call_id']: row for row in dispatched}
    rejected_inputs = set()
    actual_inputs = [row for row in dispatched if row['tool'] == 'type_text']
    if allow_rejected_input is True and len(inputs) == len(actual_inputs) == 1:
        sources = [row for row in states if row['value'].get('snapshot_id') == inputs[0]['snapshot_id']]
        if len(sources) == 1:
            for call in dispatched:
                if call['tool'] != 'rejected_type_text': continue
                matches = [row for row in returned if row['call_id'] == call['call_id']]
                if (len(matches) == 1 and matches[0]['event'] == 'result'
                        and matches[0].get('tool') == 'rejected_type_text'
                        and matches[0].get('value') == {'status': 'refused', 'reason': 'DESKTOP_REQUEST_REJECTED'}
                        and call['at'] <= matches[0]['at'] < sources[0]['at'] < actual_inputs[0]['at']):
                    rejected_inputs.add(call['call_id'])
    missing_reads = set()
    if allow_missing_result_read is True:
        writes = [row for row in dispatched if row['tool'] == 'write_result']
        if len(writes) == 1:
            write = writes[0]
            written = [row for row in returned if row['call_id'] == write['call_id']]
            fresh = [row for row in states if row['value'].get('snapshot_id') == fresh_state.get('snapshot_id')]
            readback = [row for row in returned if row['event'] == 'result' and row.get('tool') == 'read_result'
                        and row.get('value') == result.decode('utf8') and row['at'] > write['at']]
            if len(written) == len(fresh) == 1 and written[0]['event'] == 'result' and readback:
                for row in returned:
                    call = calls.get(row['call_id'], {})
                    if (row['event'] == 'error' and row.get('tool') == 'read_result'
                            and row.get('error') == 'FileNotFoundError' and call.get('tool') == 'read_result'
                            and call['at'] <= row['at'] < fresh[0]['at'] < write['at']
                            and sum(item['call_id'] == row['call_id'] for item in returned) == 1):
                        missing_reads.add(row['call_id'])
    native = body_from_state(fresh_state).encode('utf8')
    permitted = {'launch_app', 'list_windows', 'get_window_state', 'type_text', 'hotkey',
                 'bring_to_front', 'write_result', 'read_result', 'rejected_write_result'}
    complete = (len(dispatched) <= 30 and len(calls) == len(dispatched) == len(returned)
                and {row['call_id'] for row in returned} == set(calls)
                and [row['used'] for row in dispatched] == list(range(1, len(dispatched) + 1))
                and all(row.get('tool') in permitted or row['call_id'] in rejected_inputs for row in dispatched)
                and not any(row['event'] == 'UNKNOWN' or (row['event'] == 'error'
                    and row.get('tool') != 'get_window_state' and row.get('call_id') not in missing_reads) for row in rows))
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
            'recovered_missing_reads': len(missing_reads),
            'recovered_input_refusals': len(rejected_inputs),
            'rule': 'all attempts retained; Save may repeat only after a new grounded observation; no edit replay'}
