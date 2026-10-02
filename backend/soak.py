"""Read-only real-duration observer. Never advances time or submits model work."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import httpx
from sqlalchemy import select
from agent.daily_report import dump, verify
from backend.checkpoint import snapshot
from backend.config import Settings
from backend.db import database
from backend.manage import load_env
from backend.models import Attempt, Task, utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True)
    parser.add_argument('--seconds', type=int, choices=[3600, 28800], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ.update(load_env())
    settings = Settings.from_env()
    output = args.output.resolve()
    if not output.is_relative_to(settings.root):
        raise ValueError('observer output must be inside private backend root')
    output.mkdir(mode=0o700)
    (output / 'samples').mkdir(mode=0o700)
    engine, sessions = database(settings.database_url)
    started = time.monotonic()
    baseline, identity, unavailable_since = None, None, None
    worker_pids, api_pids = set(), set()
    def pids(pattern):
        found = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True)
        return found.stdout.split()
    with httpx.Client(base_url='http://127.0.0.1:18089', trust_env=False, timeout=5,
                      headers={'Authorization': 'Bearer ' + settings.api_token}) as client:
        for index in range(args.seconds // 15 + 30):
            elapsed = time.monotonic() - started
            record = {'at': utcnow().isoformat(), 'elapsedSeconds': elapsed}
            try:
                response = client.get('/tasks/' + args.task)
                response.raise_for_status()
                state = response.json()
            except httpx.HTTPError:
                unavailable_since = unavailable_since or time.monotonic()
                record['api'] = 'temporarily_unavailable'
                dump(output / 'samples' / f'{index:05d}.json', record)
                if time.monotonic() - unavailable_since > 90:
                    raise RuntimeError('API_UNAVAILABLE_OVER_90_SECONDS')
                time.sleep(15)
                continue
            unavailable_since = None
            record['task'] = state
            record['workerPids'] = pids(r'^.*/python -m backend.worker$')
            record['apiPids'] = pids(r'^.*/python -m uvicorn backend.api:production_app ')
            worker_pids.update(record['workerPids']); api_pids.update(record['apiPids'])
            with sessions() as db:
                task = db.get(Task, args.task)
                if task.session_id:
                    if identity and task.session_id != identity:
                        raise RuntimeError('SESSION_CHANGED')
                    identity = task.session_id
                if task.status == 'WAITING_RELEASE':
                    current = snapshot(task.run_dir, baseline)
                    if baseline and current != baseline:
                        raise RuntimeError('WAITING_EVIDENCE_CHANGED')
                    if set(current['artifacts']) != {'report.json'} or current['pending']:
                        raise RuntimeError('INVALID_WAITING_DRAFT')
                    baseline = current
                    record['waitingEvidence'] = current
                dump(output / 'samples' / f'{index:05d}.json', record)
                if task.status == 'SUCCEEDED':
                    if elapsed < args.seconds or baseline is None or len(worker_pids) < 2 or len(api_pids) < 2:
                        raise RuntimeError('DURATION_OR_RESTART_EVIDENCE_INCOMPLETE')
                    snapshot(task.run_dir, baseline)
                    attempts = list(db.scalars(select(Attempt).where(Attempt.task_id == task.id).order_by(Attempt.id)))
                    if len(attempts) != 2 or attempts[-1].started_at < task.release_at:
                        raise RuntimeError('RELEASE_ATTEMPT_INVALID')
                    result = verify(task.run_dir, continuation=True)
                    result.update(elapsedSeconds=elapsed, requiredSeconds=args.seconds,
                                  workerPids=sorted(worker_pids), apiPids=sorted(api_pids), samples=index + 1)
                    dump(output / 'verification.json', result)
                    print(json.dumps({'result': 'PASS', 'taskId': task.id, 'elapsedSeconds': elapsed}), flush=True)
                    return
                if task.status not in ('QUEUED', 'RUNNING', 'WAITING_RELEASE'):
                    raise RuntimeError('TASK_NOT_SUCCESSFUL_' + task.status)
            if elapsed > args.seconds + 300:
                raise RuntimeError('REAL_DURATION_DEADLINE_EXCEEDED')
            time.sleep(15)
    raise RuntimeError('OBSERVER_LIMIT_REACHED')


if __name__ == '__main__':
    main()
