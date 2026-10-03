"""Read-only periodic receipts; never creates work, grants quota or marks notices read."""
import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import httpx
from agent.daily_report import dump, require, sha, verify
from backend.batches import digest
from backend.config import Settings
from backend.db import database
from backend.manage import load_env
from backend.models import Occurrence, Task, utcnow
from backend.workflow_sources import operations_snapshot, project_snapshot


def reconstruct_sources(sources):
    """Rebuild frozen metadata, not a later mutable database query."""
    require(len(sources) == 2 and [s['workflow'] for s in sources] ==
            ['project-changes', 'task-operations'], 'two fixed sources required')
    project, operations = sources
    p, o = project['source'], operations['source']
    require(project_snapshot(p['fromExclusive'], p['toInclusive'], project['payload']['date']) == project,
            'pinned Git source differs')
    records = [dict(id=r['id'], status=r['status'], calls=r['calls'], updatedAt=r['updatedAt'],
                    usage=dict(r['usage'], available=True) if r['usageKnown'] else None) for r in o['tasks']]
    rebuilt = operations_snapshot(records, datetime.fromisoformat(o['fromInclusive']),
                                  datetime.fromisoformat(o['toExclusive']), operations['payload']['date'])
    require(rebuilt == operations, 'frozen operations source differs')


def assess(plan, receipts, now):
    """Pure gate for tests. The CLI always supplies actual utcnow()."""
    start = datetime.fromisoformat(plan['config']['startAt'])
    end = start + timedelta(days=7)
    checks = {'sevenRuns': plan['config']['runs'] == 7,
              'realDurationReached': now >= end,
              'allOccurrences': len(plan['items']) == len(receipts) == plan['occurrences'] == 7,
              'continuousDays': [datetime.fromisoformat(i['due_at']) for i in plan['items']] ==
                                [start + timedelta(days=i) for i in range(7)],
              'allVerified': bool(receipts) and all(r.get('status') == 'VERIFIED' for r in receipts)}
    tasks = [t for r in receipts for t in r.get('tasks', [])]
    checks['uniqueFourteenTasks'] = len(tasks) == len({t['id'] for t in tasks}) == 14
    sessions = [t.get('session_id') for t in tasks]
    checks['uniqueFourteenSessions'] = None not in sessions and len(set(sessions)) == len(sessions) == 14
    checks['receiptIdentities'] = [r['id'] for r in receipts] == [r['id'] for r in plan['items']]
    last_commit = plan['config'].get('baselineCommit')
    continuous_sources = last_commit is not None
    for receipt in receipts:
        binding = receipt.get('projectRange', {})
        continuous_sources = continuous_sources and binding.get('fromExclusive') == last_commit
        last_commit = binding.get('toInclusive')
    checks['continuousGitRanges'] = continuous_sources
    return {'status': 'PASS' if all(checks.values()) else 'INCOMPLETE', 'checks': checks,
            'observedAt': now.isoformat(), 'observationStart': start.isoformat(), 'observationEnd': end.isoformat(),
            'userAdoption': 'NOT_ASSESSED', 'scope': 'periodic execution, not continuous uptime'}


def get(client, url, **kwargs):
    response = client.get(url, **kwargs)
    response.raise_for_status()
    return response


def verify_api_evidence(state, verdict):
    usage = state.get('usage') or {}
    require(verdict['sessionId'] == state['session_id'] and
            all(usage.get(k) == value for k, value in verdict['usage'].items()) and
            usage.get('models') == [verdict['model']] and
            verdict['rawCalls'] == state['budget']['used'] <= 30 and state['budget']['limit'] == 30,
            'API and original evidence differ')


def notices(client):
    result, cursor = [], 0
    while True:
        page = get(client, '/notifications', params={'after': cursor, 'limit': 100}).json()
        result.extend(page['items'])
        if len(page['items']) < 100:
            return result
        require(page['next_cursor'] > cursor, 'notification cursor did not advance')
        cursor = page['next_cursor']


def inspect_occurrence(client, sessions, item, inbox, output):
    record = dict(item, tasks=[], status='INCOMPLETE')
    if item['status'] != 'SUBMITTED':
        record['reason'] = item['status']
        return record
    batch = get(client, '/batches/' + item['batch_id']).json()
    dump(output / (item['id'] + '-batch.json'), batch)
    record['batch'] = batch
    with sessions() as db:
        saved = db.get(Occurrence, item['id'])
        require(saved is not None and saved.batch_id == item['batch_id'], 'occurrence binding differs')
        sources = saved.source
        require(digest(sources) == saved.source_sha256 == item['source_sha256'], 'source hash differs')
    reconstruct_sources(sources)
    record['projectRange'] = {k: sources[0]['source'][k] for k in ('fromExclusive', 'toInclusive')}
    due = datetime.fromisoformat(item['due_at'])
    operation_source = sources[1]['source']
    require(datetime.fromisoformat(operation_source['fromInclusive']) == due - timedelta(days=1) and
            datetime.fromisoformat(operation_source['toExclusive']) == due, 'source window differs')
    dump(output / (item['id'] + '-sources.json'), sources)
    require(len(batch['items']) == 2, 'two task batch required')
    for index, state in enumerate(batch['items']):
        result = dict(state, verification=None, notifications=[n for n in inbox if n['task_id'] == state['id']])
        record['tasks'].append(result)  # Preserve failures and their recorded usage, including null.
        require(due <= datetime.fromisoformat(state['created_at']) <= due + timedelta(minutes=10),
                'task creation outside occurrence grace period')
        with sessions() as db:
            task = db.get(Task, state['id'])
            require(task is not None and task.payload == dict(sources[index]['payload'], inputMode='aggregate'),
                    'task payload differs from frozen source')
            run_dir = task.run_dir
        if state['status'] != 'SUCCEEDED':
            continue
        verdict = verify(run_dir, aggregate=True)
        verify_api_evidence(state, verdict)
        current = [n for n in result['notifications'] if n['status_at_event'] == n['current_status'] == 'SUCCEEDED']
        require(len(current) == 1, 'one success notification required')
        expected_urls = ['/tasks/' + state['id'] + '/artifacts/' + name for name in ('report.json', 'report.md')]
        require(sorted(current[0]['artifact_urls']) == sorted(expected_urls), 'notification URLs differ')
        for url in expected_urls:
            response = get(client, url)
            name = url.rsplit('/', 1)[-1]
            checksum = verdict['artifacts'][name]
            require(sha(response.content) == checksum and response.headers.get('etag') == '"' + checksum + '"',
                    'download checksum differs')
            with (output / (state['id'] + '-' + name)).open('xb') as file:
                os.chmod(file.name, 0o600)
                file.write(response.content)
        result['verification'] = verdict
    if batch['status'] == 'SUCCEEDED' and all(t['verification'] for t in record['tasks']):
        record['status'] = 'VERIFIED'
    return record


def observe(client, sessions, identity, output):
    output = Path(output).absolute()
    output.mkdir(mode=0o700)  # Every observation has a new directory; no overwrites.
    record = {'scheduleId': identity, 'startedAt': utcnow().isoformat(), 'items': []}
    try:
        plan = get(client, '/schedules/' + identity).json()
        record['plan'] = plan
        dump(output / 'plan.json', plan)
        inbox = notices(client)
        for item in plan['items']:
            try:
                receipt = inspect_occurrence(client, sessions, item, inbox, output)
            except Exception as error:
                receipt = dict(item, status='CHECK_FAILED', errorType=type(error).__name__)
                saved_batch = output / (item['id'] + '-batch.json')
                if saved_batch.exists():
                    receipt['tasks'] = json.loads(saved_batch.read_text())['items']
            record['items'].append(receipt)
        record['assessment'] = assess(plan, record['items'], utcnow())
    except Exception as error:
        record['assessment'] = {'status': 'INCOMPLETE', 'errorType': type(error).__name__}
    dump(output / 'receipt.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ.update(load_env())
    settings = Settings.from_env()
    require(args.output.resolve().is_relative_to(settings.root), 'output must be inside private backend root')
    _, sessions = database(settings.database_url)
    with httpx.Client(base_url='http://127.0.0.1:18089', trust_env=False, timeout=20,
                      headers={'Authorization': 'Bearer ' + settings.api_token}) as client:
        result = observe(client, sessions, args.schedule, args.output)
    print(json.dumps({'receipt': str(args.output / 'receipt.json'), 'assessment': result['assessment']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
