"""Match ordered official tool exchanges to a separately verified guest trace.

Does not authenticate the session, its final report, or attachment image bytes.
Harness may transcode guest PNGs to WebP; attachment IDs are not PNG hashes.
"""
import hashlib
import re
from handoff_evidence import strict_json, same_json
from handoff_trace import verify_handoff_trace
from handoff_observation import project_handoff_observation


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_EXCHANGES_UNVERIFIED')


def match_handoff_exchanges(official, trace, *, run_id, materials, expected, session_id=None):
    verified = verify_handoff_trace(trace, run_id=run_id, materials=materials, expected=expected, session_id=session_id)
    source = strict_json(materials)
    hashes = {**{'notes/' + n['id']: hashlib.sha256(n['content'].encode()).hexdigest() for n in source['notes']},
              **{k: hashlib.sha256(source[k].encode()).hexdigest() for k in ('tasksCsv', 'previousReport')}}
    raw_calls = {r['call_id']: r for r in trace if r['event'] == 'dispatch'}
    raw_results = {r['call_id']: r['value'] for r in trace if r['event'] == 'result'}
    by_used = {r['used']: r for r in raw_calls.values()}
    states, logical = {}, []
    current = None
    intent = next(r for r in trace if r['event'] == 'handoff_reopen_intent')
    helper_args = {r['call_id']: r['args'] for r in trace if r['event'] == 'helper_arguments'}
    for row in trace:
        event = row['event']
        if event == 'dispatch': current = row
        if event == 'observation_evidence':
            state = raw_results[by_used[row['used']]['call_id']]
            states[state['snapshot_id']] = state
            logical.append(('vm_observe', {}, project_handoff_observation(state, row['used'])))
        elif event in ('attempted_input', 'attempted_save'):
            state = states[row['snapshot_id']]
            args = dict(snapshot_id=row['snapshot_id'])
            if event == 'attempted_input':
                candidates = [e for e in state.get('elements', []) if e.get('element_index') == row['element_index']
                              and e.get('role') == 'AXTextArea' and e.get('enabled', True) is True]
                require(len(candidates) == 1 and type(candidates[0].get('element_token')) is str)
                args.update(element_index=row['element_index'], element_token=candidates[0]['element_token'], text=expected.decode())
            logical.append(('vm_type' if event == 'attempted_input' else 'vm_save', args, raw_results[current['call_id']]))
        elif event == 'handoff_window_reopened':
            logical.append(('vm_reopen', dict(snapshot_id=intent['snapshot_id']),
                            dict(requires_new_observation=True, used=row['used'])))
        elif event == 'result':
            used = raw_calls[row['call_id']]['used']
            if row['tool'] == 'read_materials':
                logical.append(('vm_read_materials', {}, dict(materials=source, sourceHashes=hashes,
                    inputSha256=verified['inputSha256'], used=used)))
            elif row['tool'] == 'write_result':
                logical.append(('vm_write_result', dict(snapshot_id=verified['finalSnapshotId'], value=expected.decode()),
                                dict(created='result.txt', value=row['value'], used=used)))
            elif row['tool'] == 'read_result':
                logical.append(('vm_read_result', {}, dict(content=row['value'], used=used)))
            elif row['tool'] in ('locate_quote', 'check_draft', 'submit_handoff'):
                logical.append(('vm_' + row['tool'], helper_args[row['call_id']], row['value']))
    require(type(official) is list and bool(official))
    events = [r for r in official if r.get('type') in ('tool/call', 'tool/result')]
    require(len(events) == 2 * len(logical))
    ids, attachments = set(), []
    last_seq = -1
    for index, (name, args, response) in enumerate(logical):
        call, result = events[index * 2:index * 2 + 2]
        require(call['type'] == 'tool/call' and result['type'] == 'tool/result')
        require(type(call.get('seq')) is int and type(result.get('seq')) is int
                and last_seq < call['seq'] < result['seq'])
        last_seq = result['seq']
        data, message = call['data'], result['data']['message']
        key = data.get('callId')
        require(type(key) is str and bool(key) and key not in ids and message.get('toolCallId') == key
                and message.get('isError', False) is False and data.get('name') == name)
        ids.add(key)
        require(type(data.get('arguments')) is str and same_json(strict_json(data['arguments'].encode()), args))
        content = message.get('content')
        require(type(content) is list and len(content) == (2 if name == 'vm_observe' else 1))
        require(type(content[0]) is dict and set(content[0]) == {'type', 'text'}
                and content[0]['type'] == 'text' and type(content[0]['text']) is str)
        require(same_json(strict_json(content[0]['text'].encode()), response))
        if name == 'vm_observe':
            image = content[1]
            require(type(image) is dict and set(image) == {'type', 'attachment'} and image['type'] == 'image')
            attachment = image['attachment']
            require(type(attachment) is dict and type(attachment.get('attachmentId')) is str
                    and re.fullmatch(r'sha256:[0-9a-f]{64}', attachment['attachmentId'])
                    and attachment.get('mediaType') in ('image/png', 'image/webp')
                    and all(type(attachment.get(k)) is int and attachment[k] > 0 for k in ('bytes', 'width', 'height')))
            attachments.append(dict(snapshotId=response['snapshot_id'], used=response['used'], attachment=dict(attachment)))
    return {'status': 'EXCHANGES_MATCHED', 'runId': run_id, 'officialToolCalls': len(logical),
            'rawCalls': verified['rawCalls'], 'attachmentsToVerify': attachments,
            'sessionVerified': False, 'imageBytesVerified': False, 'semanticVerified': False}
