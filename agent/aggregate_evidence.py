"""Independent P4 input evidence checks. Read-only; never creates business output."""
import json
from pathlib import Path
try:
    from .daily_report import require, same, sha, text_file
except ImportError:  # direct daily_report.py CLI
    from daily_report import require, same, sha, text_file


def verify_inputs(parent, audit, workspace, oracle):
    """Validate one parsed aggregate call and return its proven source observations."""
    require(parent['name'] == 'workspace_report_inputs' and parent['args'] == {}, 'invalid aggregate invocation')
    value = parent['value']
    require(isinstance(value, dict) and set(value) == {'task', 'notes', 'csv'}, 'aggregate output fields')
    root = Path(workspace)
    task_bytes, task_text = text_file(root / 'task.json')
    require(sha(task_bytes) == oracle['taskSha256'], 'task changed')
    task = json.loads(task_text)
    require(task['notes'] == [n['path'] for n in oracle['expected']['notes']]
            and [c['path'] for c in task['csv']] == [c['path'] for c in oracle['expected']['csv']], 'task sources changed')
    require(isinstance(value['notes'], list) and len(value['notes']) == len(task['notes'])
            and isinstance(value['csv'], list) and len(value['csv']) == len(task['csv']), 'aggregate source count')
    items = [('workspace_read', {'path': 'task.json'}, value['task'])]
    items.extend(('workspace_read', {'path': path}, observation)
                 for path, observation in zip(task['notes'], value['notes']))
    items.extend(('workspace_csv_stats', spec, observation)
                 for spec, observation in zip(task['csv'], value['csv']))
    call_id = parent['callId']
    def event(kind, cid, name):
        found = [(i, a) for i, a in enumerate(audit) if a['event'] == kind and a.get('callId') == cid]
        require(len(found) == 1 and found[0][1]['name'] == name, 'aggregate audit correlation')
        return found[0]
    start, _ = event('dispatch', call_id, parent['name'])
    end, parent_done = event('result', call_id, parent['name'])
    require(parent_done['outcome'] == 'returned' and start < end, 'aggregate failed')
    expected_ids = {call_id + ':input-' + str(i) for i in range(1, len(items) + 1)}
    actual_ids = {a.get('callId') for a in audit if isinstance(a.get('callId'), str)
                  and a['callId'].startswith(call_id + ':input-')}
    require(actual_ids == expected_ids, 'extra or missing aggregate children')
    observations, previous = [], start
    for index, (name, args, result) in enumerate(items, 1):
        require(isinstance(result, dict), 'invalid aggregate item')
        path = args['path']
        data, source = text_file(root / path)
        expected_sha = oracle['taskSha256'] if path == 'task.json' else oracle['inputs'][path]
        require(sha(data) == expected_sha, 'aggregate source changed')
        if name == 'workspace_read':
            require(result.get('path') == path and result.get('sha256') == expected_sha
                    and type(result.get('bytes')) is int and result['bytes'] == len(data)
                    and result.get('truncated') is False and result.get('startLine') == 1
                    and result.get('content') == source.replace('\r\n', '\n').replace('\r', '\n'),
                    'aggregate read differs from complete source')
        else:
            table = oracle['expected']['csv'][index - 2 - len(task['notes'])]
            require(same(result, table) and args['numericColumns'] == list(table['numeric']), 'aggregate CSV differs from oracle')
        cid = call_id + ':input-' + str(index)
        dispatched, d = event('dispatch', cid, name)
        returned, r = event('result', cid, name)
        require(previous < dispatched < returned < end, 'aggregate internal order')
        encoded = json.dumps(args, ensure_ascii=False, separators=(',', ':'))
        require(d['arguments'] == {'bytes': len(encoded.encode()), 'sha256': sha(encoded)}, 'aggregate internal arguments')
        require(r['outcome'] == 'returned' and r.get('artifact') == {'bytes': len(data), 'sha256': expected_sha},
                'aggregate internal result evidence')
        previous = returned
        observations.append({'name': name, 'args': args, 'value': result, 'seq': parent['seq'], 'end': parent['end']})
    return observations
