"""Read-only project/operations snapshots. No model, submission or arbitrary shell."""
import csv
from datetime import datetime
import io
import json
from pathlib import Path
import re
import subprocess
from agent.daily_report import dump, require, sha
from backend.schemas import Submission

PROJECT = Path(__file__).resolve().parents[1]
TOKEN_FIELDS = ('inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'totalTokens')
STATES = {'QUEUED', 'RUNNING', 'WAITING_RELEASE', 'STOP_REQUESTED', 'SUCCEEDED',
          'FAILED', 'BLOCKED', 'UNVERIFIED', 'STOPPED'}


def window(start, end):
    require(isinstance(start, datetime) and isinstance(end, datetime) and
            start.tzinfo is not None and end.tzinfo is not None and start < end,
            'explicit nonempty timezone-aware window required')
    return {'fromInclusive': start.isoformat(), 'toExclusive': end.isoformat()}


def table(headers, rows):
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def payload(day, title, progress, blockers, next_step, csv_text, columns):
    body = {'date': day, 'notes': [{'name': 'source.md', 'content':
        f'# {title}\n\n## 进展\n{progress}\n\n## 阻塞\n{blockers}\n\n## 下一步\n{next_step}\n'}],
        'csv': [{'name': 'facts.csv', 'content': csv_text, 'numericColumns': columns}]}
    return Submission.model_validate(body).model_dump(mode='json', exclude_none=True)


def project_snapshot(start_commit, end_commit, day):
    # Only this repository, exact commit identities, fixed commands, no shell expansion.
    require(all(isinstance(v, str) and re.fullmatch('[0-9a-f]{40}', v)
                for v in (start_commit, end_commit)), 'full commit identities required')
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=PROJECT, timeout=20)
    git('merge-base', '--is-ancestor', start_commit, end_commit)
    ids = git('rev-list', '--reverse', start_commit + '..' + end_commit).decode().splitlines()
    require(len(ids) <= 20, 'more than 20 commits; choose an explicit smaller interval')
    facts = []
    for commit in ids:
        # Compare each commit with its first parent; do not duplicate merge parents.
        parents = git('rev-list', '--parents', '-n', '1', commit).decode().split()
        require(len(parents) >= 2, 'parent required in bounded commit interval')
        raw = git('diff', '--numstat', '-z', '--no-renames', parents[1], commit, '--')
        files, binary, added, removed = 0, 0, 0, 0
        for row in raw.split(b'\0'):
            if not row:
                continue
            a, d, _path = row.split(b'\t', 2)
            files += 1
            if a == b'-' or d == b'-': binary += 1
            else:
                require(a.isdigit() and d.isdigit(), 'invalid git statistics')
                added += int(a); removed += int(d)
        facts.append({'commit': commit, 'parent': parents[1], 'files': files,
                      'binaryFiles': binary, 'addedLines': added, 'removedLines': removed,
                      'gitStatisticsSha256': sha(raw)})
    progress = f'固定提交范围：{start_commit}..{end_commit}；共{len(facts)}个提交。'
    progress += '\n仅统计已提交变更，不含未提交文件；合并提交与第一父提交比较。'
    body = payload(day, '项目变更简报', progress, '未评估需求完成度或代码质量。',
                   '按提交身份查看需要人工复核的变更。',
                   table(['commit', 'files', 'binaryFiles', 'addedLines', 'removedLines'],
                         [[r[k] for k in ('commit', 'files', 'binaryFiles', 'addedLines', 'removedLines')] for r in facts]),
                   ['files', 'binaryFiles', 'addedLines', 'removedLines'])
    return {'workflow': 'project-changes', 'source': {'fromExclusive': start_commit,
            'toInclusive': end_commit, 'commits': facts}, 'payload': body}


def operations_snapshot(records, start, end, day):
    interval = window(start, end)
    require(isinstance(records, list) and len(records) <= 100, 'bounded complete task list required')
    facts, seen = [], set()
    for record in records:
        identity = record['id']
        require(isinstance(identity, str) and re.fullmatch('[0-9a-f-]{36}', identity) and
                identity not in seen, 'unique task UUID required')
        seen.add(identity)
        require(record['status'] in STATES, 'unknown task state')
        require(type(record['calls']) is int and 0 <= record['calls'] <= 30, 'invalid raw budget')
        updated = datetime.fromisoformat(record['updatedAt'])
        require(updated.tzinfo is not None and start <= updated < end, 'task outside frozen window')
        usage = record.get('usage')
        known = isinstance(usage, dict) and usage.get('available') is True and all(
            type(usage.get(k)) is int and usage[k] >= 0 for k in TOKEN_FIELDS)
        if known:
            require(usage['totalTokens'] == sum(usage[k] for k in TOKEN_FIELDS[:-1]), 'inconsistent usage')
        facts.append({'id': identity, 'status': record['status'], 'calls': record['calls'],
                      'updatedAt': updated.isoformat(), 'usageKnown': known,
                      'usage': {k: usage[k] for k in TOKEN_FIELDS} if known else None})
    facts.sort(key=lambda r: r['id'])
    unknown = sum(not f['usageKnown'] for f in facts)
    headers = ['task', 'state', 'rawCalls', 'usageKnown', *TOKEN_FIELDS]
    rows = [[f['id'], f['status'], f['calls'], int(f['usageKnown']),
             *[f['usage'][k] if f['usageKnown'] else '' for k in TOKEN_FIELDS]] for f in facts]
    body = payload(day, '任务运行与用量日报',
        f'窗口[{start.isoformat()}, {end.isoformat()})；按updatedAt选择，共{len(facts)}个任务。\n状态和用量为采集时快照，不推断未记录的历史状态。',
        f'{unknown}个任务用量不完整；空白表示未知，不是零。缓存不等于现金费用。',
        '复核FAILED、BLOCKED、UNVERIFIED、STOPPED及缺失用量的任务；不自动重跑。',
        table(headers, rows), ['rawCalls', 'inputTokens', 'outputTokens', 'totalTokens'])
    # Two bounded tables expose every token category despite the four-column stats limit.
    body['csv'] = [
        {'name': 'tasks.csv', 'content': table(['task', 'state', 'rawCalls', 'usageKnown', 'cacheWriteTokens'],
            [[f['id'], f['status'], f['calls'], int(f['usageKnown']),
              f['usage']['cacheWriteTokens'] if f['usageKnown'] else ''] for f in facts]),
         'numericColumns': ['rawCalls', 'usageKnown', 'cacheWriteTokens']},
        {'name': 'usage.csv', 'content': table(['task', 'inputTokens', 'outputTokens', 'cacheReadTokens', 'totalTokens'],
            [[f['id'], *[f['usage'][k] if f['usageKnown'] else '' for k in
                        ('inputTokens', 'outputTokens', 'cacheReadTokens', 'totalTokens')]] for f in facts]),
         'numericColumns': ['inputTokens', 'outputTokens', 'cacheReadTokens', 'totalTokens']}]
    body = Submission.model_validate(body).model_dump(mode='json', exclude_none=True)
    return {'workflow': 'task-operations', 'source': {**interval, 'tasks': facts}, 'payload': body}


def collect_operations(sessions, start, end, day):
    from sqlalchemy import select
    from backend.models import Task, Usage
    window(start, end)
    with sessions() as db:
        rows = db.execute(select(Task.id, Task.status, Task.calls, Task.updated_at, Usage.data)
                          .outerjoin(Usage, Usage.task_id == Task.id)
                          .where(Task.updated_at >= start, Task.updated_at < end)
                          .order_by(Task.id).limit(101)).all()
    return operations_snapshot([dict(id=r[0], status=r[1], calls=r[2], updatedAt=r[3].isoformat(),
                                     usage=r[4]) for r in rows], start, end, day)


def freeze_snapshot(snapshot, output):
    # Validate before creating anything. Never silently replace a previous observation.
    Submission.model_validate(snapshot['payload'])
    require(snapshot['workflow'] in ('project-changes', 'task-operations'), 'unknown workflow')
    root = Path(output).absolute()
    require(not root.exists(), 'snapshot already exists')
    root.mkdir(mode=0o700, parents=True)
    dump(root / 'snapshot.json', snapshot)
    return {'workflow': snapshot['workflow'], 'path': str(root / 'snapshot.json'),
            'sha256': sha((root / 'snapshot.json').read_bytes())}
