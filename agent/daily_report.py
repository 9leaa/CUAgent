"""P1 developer-side preparation and independent acceptance; never a model tool."""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import uuid
from datetime import date, datetime
from pathlib import Path

TOOLS = ['calculate', 'workspace_image_probe', 'workspace_list', 'workspace_read',
         'workspace_write', 'workspace_csv_stats']
DAILY_TOOLS = ['workspace_list', 'workspace_read', 'workspace_write', 'workspace_csv_stats', 'workspace_daily_report']
MODEL = {'provider': 'deepseek-account', 'model': 'deepseek-flash', 'reasoningEffort': 'off'}


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def same(left, right):
    """JSON equality without Python's True == 1 coercion."""
    if isinstance(right, dict):
        return isinstance(left, dict) and left.keys() == right.keys() and all(same(left[k], v) for k, v in right.items())
    if isinstance(right, list):
        return isinstance(left, list) and len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    if type(right) in (int, float):
        return type(left) in (int, float) and math.isfinite(left) and left == right
    return type(left) is type(right) and left == right


def report_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate report field')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def dump(path, value):
    with path.open('x', encoding='utf8') as file:
        path.chmod(0o600)
        json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')


def text_file(path, limit=65536):
    require(path.is_file() and not path.is_symlink(), 'regular input file required')
    data = path.read_bytes()
    require(len(data) <= limit, 'input too large')
    text = data.decode('utf8')
    require('\0' not in text and not text.startswith('\ufeff'), 'unsupported NUL/BOM')
    return data, text


def note_record(path, data):
    text = data.decode('utf8').replace('\r\n', '\n').replace('\r', '\n')
    lines = text.splitlines()
    require(lines and lines[0].startswith('# ') and lines[0][2:].strip(), 'note title required')
    labels = {'进展': 'progress', '阻塞': 'blockers', '下一步': 'next'}
    values, current = {}, None
    for line in lines[1:]:
        if line.startswith('## '):
            label = line[3:]
            require(label in labels and labels[label] not in values, 'unknown/duplicate note heading')
            current = labels[label]
            values[current] = []
        elif current is not None:
            require(not line.startswith('#'), 'nested headings not supported')
            values[current].append(line)
        else:
            require(not line.strip(), 'content before sections')
    require(set(values) == set(labels.values()), 'all note sections required')
    fields = {key: '\n'.join(value).strip() for key, value in values.items()}
    require(all(fields.values()), 'empty note section; use 无 explicitly')
    require(len(lines) <= 40 and len(data) <= 6000, 'note exceeds P1 report limit')
    return {'path': path, 'sha256': sha(data), 'title': lines[0][2:].strip(), **fields}


def csv_oracle(path, data, columns):
    """Uses Python csv, independently of the JavaScript tool implementation."""
    rows = list(csv.reader(io.StringIO(data.decode('utf8'), newline=''), strict=True))
    require(rows and 1 <= len(rows[0]) <= 100 and len(rows) <= 10001, 'CSV dimensions')
    headers = rows[0]
    require(all(headers) and len(set(headers)) == len(headers), 'CSV duplicate/empty header')
    require(all(len(row) == len(headers) for row in rows[1:]), 'CSV ragged row')
    require(isinstance(columns, list) and 1 <= len(columns) <= 4 and
            all(isinstance(c, str) and c in headers and '|' not in c and '\n' not in c for c in columns)
            and len(set(columns)) == len(columns), 'invalid numeric columns')
    numeric = {}
    for column in columns:
        values = []
        for row in rows[1:]:
            value = row[headers.index(column)].strip()
            if value:
                require(re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value), 'non-numeric cell')
                number = float(value)
                require(math.isfinite(number), 'non-finite cell')
                values.append(number)
        total = sum(values)
        require(math.isfinite(total), 'numeric overflow')
        numeric[column] = {'count': len(values), 'missing': len(rows) - 1 - len(values),
                           'sum': total, 'min': min(values) if values else None,
                           'max': max(values) if values else None,
                           'mean': total / len(values) if values else None}
    return {'path': path, 'rowCount': len(rows) - 1, 'columnCount': len(headers),
            'columns': headers, 'numeric': numeric, 'bytes': len(data), 'sha256': sha(data)}


def number(value):
    if value is None:
        return 'null'
    return str(int(value)) if value == int(value) else str(value)


def markdown(report):
    lines = [f'# 日报 {report["date"]}', '']
    for note in report['notes']:
        lines += [f'## {note["title"]}', f'来源: {note["path"]}', f'SHA-256: {note["sha256"]}',
                  '### 进展', note['progress'], '### 阻塞', note['blockers'], '### 下一步', note['next'], '']
    for table in report['csv']:
        lines += [f'## 数据 {table["path"]}', f'SHA-256: {table["sha256"]}',
                  f'数据行: {table["rowCount"]}',
                  '| 列 | 有效 | 缺失 | 合计 | 最小 | 最大 | 均值 |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for column, stats in table['numeric'].items():
            lines.append('| ' + column + ' | ' + ' | '.join(number(stats[k]) for k in
                         ['count', 'missing', 'sum', 'min', 'max', 'mean']) + ' |')
        lines.append('')
    return '\n'.join(lines)


def prepare(spec_path, run_dir, renderer=True):
    spec_path = Path(spec_path).resolve(strict=True)
    spec = json.loads(spec_path.read_text())
    require(set(spec) == {'date', 'notes', 'csv'}, 'spec keys must be date/notes/csv')
    require(date.fromisoformat(spec['date']).isoformat() == spec['date'], 'ISO date required')
    require(isinstance(spec['notes'], list) and 1 <= len(spec['notes']) <= 3, '1–3 notes required')
    require(isinstance(spec['csv'], list) and 1 <= len(spec['csv']) <= 2, '1–2 CSVs required')
    inputs, notes, tables, csv_tasks = {}, [], [], []
    def source(name, suffix):
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]+\.' + suffix, name), 'simple relative filename required')
        require(name not in inputs, 'duplicate input')
        data, _ = text_file(spec_path.parent / name)
        path = 'inputs/' + name
        inputs[path] = data.decode('utf8')
        return path, data
    for name in spec['notes']:
        path, data = source(name, 'md')
        notes.append(note_record(path, data))
    for item in spec['csv']:
        require(isinstance(item, dict) and set(item) == {'path', 'numericColumns'}, 'invalid CSV spec')
        path, data = source(item['path'], 'csv')
        tables.append(csv_oracle(path, data, item['numericColumns']))
        csv_tasks.append({'path': path, 'numericColumns': item['numericColumns']})
    expected = {'date': spec['date'], 'notes': notes, 'csv': tables}
    expected_md = markdown(expected)
    require(len(expected_md.splitlines()) < 180 and len(expected_md.encode()) < 50000 and
            len(json.dumps(expected, ensure_ascii=False).encode()) < 50000, 'report exceeds full-readback limit')
    run_dir = Path(run_dir).absolute()
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run_dir.name), 'invalid run name')
    require(not run_dir.exists(), 'run exists; inspect original, do not overwrite')
    run_dir.mkdir(mode=0o700, parents=True)
    workspace = run_dir / 'workspace'
    (workspace / 'inputs').mkdir(mode=0o700, parents=True)
    (run_dir / 'audit').mkdir(mode=0o700)
    for path, text in inputs.items():
        target = workspace / path
        with target.open('x', encoding='utf8', newline='') as file:
            file.write(text)
        target.chmod(0o400)
    task = {'version': 1, 'date': spec['date'], 'notes': [n['path'] for n in notes], 'csv': csv_tasks,
            'workflow': 'renderer-v1' if renderer else 'model-v1'}
    dump(workspace / 'task.json', task)
    (workspace / 'task.json').chmod(0o400)
    oracle = {'expected': expected, 'inputs': {path: sha(text) for path, text in inputs.items()},
              'taskSha256': sha((workspace / 'task.json').read_bytes())}
    dump(run_dir / 'oracle.json', oracle)
    approval = {'runId': run_dir.name, 'sessionId': 'session-' + str(uuid.uuid4()),
                'workspaceRoot': str(workspace), 'ledgerPath': str(run_dir / 'audit/calls.jsonl'),
                'allowedTools': DAILY_TOOLS if renderer else TOOLS}
    dump(run_dir / 'approval.json', approval)
    return {'runId': run_dir.name, 'state': 'PREPARED', 'inputs': len(inputs), 'model': MODEL}


def verify(run_dir, *, continuation=False):
    root = Path(run_dir)
    task = json.loads((root / 'approval.json').read_text())
    renderer = 'workspace_daily_report' in task['allowedTools']
    allowed = DAILY_TOOLS if renderer else TOOLS
    require(task['allowedTools'] == allowed, 'unexpected approved capabilities')
    oracle = json.loads((root / 'oracle.json').read_text())
    workspace = Path(task['workspaceRoot'])
    for path, digest in {**oracle['inputs'], 'task.json': oracle['taskSha256']}.items():
        require(sha(text_file(workspace / path)[0]) == digest, 'input changed: ' + path)
    expected = oracle['expected']
    json_bytes, json_text = text_file(workspace / 'report.json')
    md_bytes, md_text = text_file(workspace / 'report.md')
    require(same(report_json(json_text), expected), 'report JSON content/provenance differs')
    require(md_text == markdown(expected), 'report Markdown differs')
    raw = (root / ('session-continuation.jsonl' if continuation else 'session.jsonl')).read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line]
    ends = [r for r in rows if r['type'] == 'turn/end']
    if continuation:
        original = (root / 'session.jsonl').read_bytes()
        plan = json.loads((root / 'continuation-plan.json').read_text())
        request = json.loads((root / 'continuation-request.json').read_text())['request']
        require(plan['sessionId'] == task['sessionId'] == request['sessionId'] and plan['runId'] == task['runId'], 'continuation identity changed')
        require(sha(original) == plan['sourceSessionSha256'] and raw.startswith(original), 'original session prefix changed')
        first_reason = ends[0]['data']['reason'] if ends else {}
        policy_stop = first_reason == {'kind': 'error', 'error': {'message': 'A1 request policy unavailable', 'code': 'UNKNOWN'}}
        require(len(ends) == 2 and (first_reason.get('kind') in ('aborted', 'completed') or policy_stop) and
                ends[1]['data']['reason']['kind'] == 'completed', 'one bounded continuation required')
        messages = [r for r in rows if r['type'] == 'user/message']
        require(len(messages) == 2 and messages[-1]['data']['source'].get('rpcId') == request['requestId'], 'continuation prompt identity mismatch')
        for name, value in plan['evidence']['artifacts'].items():
            current = (workspace / name).read_bytes()
            require(value == {'bytes': len(current), 'sha256': sha(current)}, 'existing artifact changed during continuation')
    else:
        require(len(ends) == 1 and ends[0]['data']['reason']['kind'] == 'completed', 'one completed original turn required')
    headers = [r['data']['header'] for r in rows if r['type'] == 'request/header']
    require(headers and all(all(h['config'].get(k) == v for k, v in MODEL.items()) for h in headers), 'model/thinking policy mismatch')
    require(all(sorted(t['name'] for t in h['tools']) == sorted(allowed) for h in headers), 'unexpected model tools')
    calls = [r for r in rows if r['type'] == 'tool/call']
    results = [r for r in rows if r['type'] == 'tool/result']
    audit_raw = Path(task['ledgerPath']).read_bytes()
    if continuation:
        checkpoint = plan['evidence']
        require(len(audit_raw) >= checkpoint['auditBytes'] and
                sha(audit_raw[:checkpoint['auditBytes']]) == checkpoint['auditSha256'], 'original audit prefix changed')
    audit = [json.loads(line) for line in audit_raw.splitlines() if line]
    dispatch = [a for a in audit if a['event'] == 'dispatch']
    if task.get('publishNotBefore'):
        require(continuation, 'scheduled report requires draft and continuation')
        publications = [a for a in dispatch if a['name'] == 'workspace_daily_report']
        require(len(publications) == 1 and
                datetime.fromisoformat(publications[0]['at'].replace('Z', '+00:00')).timestamp() * 1000 >= task['publishNotBefore'],
                'publication preceded approved deadline')
    returned = [a for a in audit if a['event'] == 'result']
    render_calls = [c for c in calls if c['data']['name'] == 'workspace_daily_report']
    require((len(render_calls) == 1 if renderer else not render_calls), 'one renderer call required')
    require(0 < len(calls) == len(results) and len(dispatch) == len(returned) == len(calls) + len(render_calls) <= 30, 'unmatched calls or budget')
    expected_ids = {c['data']['callId'] for c in calls} | {c['data']['callId'] + ':daily-source' for c in render_calls}
    require({a['callId'] for a in dispatch} == {a['callId'] for a in returned} == expected_ids, 'unmatched internal request')
    require([a['used'] for a in dispatch] == list(range(1, len(dispatch) + 1)), 'non-continuous budget')
    require(len({c['data']['callId'] for c in calls}) == len(calls), 'duplicate call')
    require(all(a['runId'] == task['runId'] and a['sessionId'] == task['sessionId'] for a in audit), 'audit identity')
    parsed = []
    for call in calls:
        c = call['data']
        result = [r for r in results if r['data']['message']['toolCallId'] == c['callId']]
        admitted = [a for a in dispatch if a['callId'] == c['callId'] and a['name'] == c['name']]
        completed = [a for a in returned if a['callId'] == c['callId'] and a['name'] == c['name']]
        require(len(result) == len(admitted) == len(completed) == 1, 'call-result correlation')
        args = json.loads(c['arguments'])
        require(admitted[0]['arguments']['sha256'] == sha(json.dumps(args, ensure_ascii=False, separators=(',', ':'))), 'argument hash')
        require(result[0]['seq'] > call['seq'], 'result precedes call')
        message = result[0]['data']['message']
        require(not message.get('isError') and completed[0]['outcome'] == 'returned', 'tool failed')
        value = json.loads(message['content'][0]['text'])
        parsed.append({'name': c['name'], 'args': args, 'value': value, 'seq': call['seq'], 'end': result[0]['seq']})
    if renderer:
        rc = render_calls[0]['data']['callId']
        child = [a for a in dispatch if a['callId'] == rc + ':daily-source'][0]
        done = [a for a in returned if a['callId'] == rc + ':daily-source'][0]
        parent = [a for a in dispatch if a['callId'] == rc][0]
        parent_done = [a for a in returned if a['callId'] == rc][0]
        require(child['name'] == done['name'] == 'workspace_read' and done['outcome'] == 'returned' and
                child['arguments']['sha256'] == sha('{"path":"report.json"}') and
                done.get('artifact') == {'bytes': len(json_bytes), 'sha256': sha(json_bytes)}, 'internal read evidence')
        require(audit.index(parent) < audit.index(child) < audit.index(done) < audit.index(parent_done), 'internal read ordering')
        render = [p for p in parsed if p['name'] == 'workspace_daily_report'][0]
        require(render['args'] == {}, 'renderer takes no path or content override')
        json_writes = [p for p in parsed if p['name'] == 'workspace_write' and p['args']['path'] == 'report.json']
        require(len(json_writes) == 1 and render['seq'] > json_writes[0]['end'], 'render precedes JSON write')
        require(render['value']['path'] == 'report.md' and render['value']['sha256'] == sha(md_bytes)
                and render['value']['bytes'] == len(md_bytes), 'renderer output hash')
        render['args'] = {'path': 'report.md', 'content': md_text}
    writes = [p for p in parsed if p['name'] in ('workspace_write', 'workspace_daily_report')]
    require(len(writes) == 2, 'only two output writes allowed')
    for path, content, data in [('report.json', json_text, json_bytes), ('report.md', md_text, md_bytes)]:
        w = [p for p in writes if p['args']['path'] == path]
        r = [p for p in parsed if p['name'] == 'workspace_read' and p['args']['path'] == path]
        require(len(w) == 1 and w[0]['args']['content'] == content, 'output not produced by actual model write')
        require(any(p['seq'] > w[0]['end'] and p['value']['content'] == content and
                    p['value']['sha256'] == sha(data) and p['value']['bytes'] == len(data) and
                    p['value']['startLine'] == 1 and not p['value']['truncated'] for p in r), 'missing full post-write readback')
    for note in expected['notes']:
        source_bytes, source_text = text_file(workspace / note['path'])
        normalized = source_text.replace('\r\n', '\n').replace('\r', '\n')
        require(any(p['name'] == 'workspace_read' and p['args']['path'] == note['path'] and
                    p['value']['sha256'] == note['sha256'] and not p['value']['truncated'] and
                    p['value'].get('content') == normalized and p['value'].get('bytes') == len(source_bytes) and
                    p['end'] < min(w['seq'] for w in writes) for p in parsed), 'missing actual source read')
    for table in expected['csv']:
        require(any(p['name'] == 'workspace_csv_stats' and same(p['value'], table) and
                    p['end'] < min(w['seq'] for w in writes) for p in parsed), 'missing independent matching statistics')
    messages = [r['data'] for r in rows if r['type'] == 'assistant/message']
    require(not any(block.get('type') == 'reasoning' and block.get('text') for m in messages
                    for block in m.get('content', [])), 'unexpected nonempty reasoning output')
    fields = ['inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'totalTokens']
    available = bool(messages) and all(isinstance(m.get('usage'), dict) and
        all(type(m['usage'].get(k)) is int and m['usage'][k] >= 0 for k in fields) for m in messages)
    usage = {'available': available, **{k: sum(m['usage'][k] for m in messages) if available else None for k in fields}}
    return {'status': 'SUCCEEDED', 'runId': task['runId'], 'sessionId': task['sessionId'],
            'calls': len(calls), 'rawCalls': len(dispatch), 'model': MODEL, 'sessionSha256': sha(raw), 'auditSha256': sha(audit_raw),
            'artifacts': {name: sha((workspace / name).read_bytes()) for name in ['report.json', 'report.md']},
            'usage': usage, 'monetaryCost': None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--spec', required=True)
    p.add_argument('--run-dir', required=True)
    p = sub.add_parser('verify')
    p.add_argument('--run-dir', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.spec, args.run_dir)
    else:
        try:
            result = verify(args.run_dir)
        except (ValueError, KeyError, OSError, TypeError, IndexError) as error:
            result = {'status': 'UNVERIFIED', 'reason': str(error)}
        dump(Path(args.run_dir) / ('verification-' + uuid.uuid4().hex + '.json'), result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get('status') != 'UNVERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
