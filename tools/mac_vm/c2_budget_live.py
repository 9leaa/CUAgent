"""Real Driver budget diagnostic; no official model or business-success claim.

Run fill and restart in separate VM Python processes against the same run.
Never changes the budget counter, manufactures calls, or deletes evidence.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

from c2_bridge import C2Task, StopRun
from driver_smoke import require_vm


def denied(task, label, operation):
    before = task.used
    try:
        operation()
    except StopRun as error:
        if error.status != 'BLOCKED':
            raise AssertionError('Expected a safe BLOCKED refusal') from error
    else:
        raise AssertionError('Exhausted task accepted ' + label)
    assert task.used == before == 30
    task.record({'event': 'c2_budget_denied', 'probe': label,
                 'used': task.used, 'executor_pid': os.getpid()})


def audit(directory):
    rows = [json.loads(line) for line in (directory / 'trace.jsonl').read_text().splitlines()]
    dispatches = [row for row in rows if row['event'] == 'dispatch']
    results = [row for row in rows if row['event'] == 'result']
    assert len(dispatches) == 30
    assert [row['used'] for row in dispatches] == list(range(1, 31))
    calls = {row['call_id'] for row in dispatches}
    assert len(calls) == 30 == len(results)
    assert {row['call_id'] for row in results} == calls
    assert all(row['tool'] in ('launch_app', 'list_windows', 'get_window_state')
               for row in dispatches)
    assert not any(row['event'] in ('UNKNOWN', 'error', 'completed_input', 'completed_action')
                   for row in rows)
    stops = [index for index, row in enumerate(rows) if row['event'] == 'stop']
    assert stops and not any(row['event'] == 'dispatch' for row in rows[stops[0] + 1:])
    snapshots = [row['value'] for row in results if row['tool'] == 'get_window_state']
    assert len(snapshots) == 28
    assert len({state['snapshot_id'] for state in snapshots}) == 28
    assert all(state['screenshot_frame_valid'] and not state.get('degraded_reason')
               for state in snapshots)
    images = sorted(directory.glob('state-*.png'))
    assert len(images) == 28 and all(path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
                                    for path in images)
    expected = {'31st_observation', 'stopped_observation', 'recovery_observation',
                'new_session_resume', 'restart_observation', 'restart_recovery', 'restart_resume'}
    assert {row['probe'] for row in rows if row['event'] == 'c2_budget_denied'} == expected
    assert not (directory / 'result.txt').exists()
    assert not (directory / 'verification.json').exists()
    initial = json.loads((directory / 'budget-fill.json').read_text())
    restarted = json.loads((directory / 'budget-restart.json').read_text())
    assert initial['executor_pid'] != restarted['executor_pid']
    assert initial['rawCalls'] == restarted['rawCalls'] == 30
    assert initial['sources'] == restarted['sources']
    return {'gateStatus': 'PASS', 'taskStatus': 'UNVERIFIED', 'rawCalls': 30,
            'scope': 'real Driver persistent budget; no official model/business evaluation',
            'restartedProcess': True, 'resetBudget': False, 'postStopDispatches': 0,
            'refusedProbes': sorted(expected), 'actualObservations': 28,
            'executorPids': [initial['executor_pid'], restarted['executor_pid']]}


def run(run_id, stage, approved):
    require_vm()
    if not approved or not re.fullmatch(r'c2_budget_[A-Za-z0-9_-]{1,60}', run_id):
        raise ValueError('Explicit approval and fixed diagnostic identity required')
    root = Path.home() / 'C0Evidence'
    if root.is_symlink():
        raise ValueError('Evidence root symlink')
    root.mkdir(mode=0o700, exist_ok=True)
    directory = root / run_id
    with (root / 'bridge.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if stage == 'audit':
            report = audit(directory)
            with (directory / 'budget-audit.json').open('x') as stream:
                json.dump(report, stream, indent=2)
            print(json.dumps(report))
            return
        if stage == 'fill' and directory.exists():
            raise ValueError('Fresh diagnostic directory required')
        if stage == 'restart' and not (directory / 'budget-fill.json').is_file():
            raise ValueError('Completed first process required')
        sources = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                   for name in ('c0_bridge.py', 'c1_bridge.py', 'c2_bridge.py', 'c2_budget_live.py')}
        task = C2Task(directory, approved=True, case_id='input_correction')
        try:
            if stage == 'fill':
                while task.used < 30:
                    task.observe()
                denied(task, '31st_observation', task.observe)
                task.stop()
                denied(task, 'stopped_observation', task.observe)
                task.claim_human()
                denied(task, 'recovery_observation', task.recovery_observe)
                denied(task, 'new_session_resume',
                       lambda: task.resume('session-budget-diagnostic-new', task.epoch))
            else:
                initial = json.loads((directory / 'budget-fill.json').read_text())
                assert initial['executor_pid'] != os.getpid()
                assert initial['sources'] == sources
                assert task.used == 30 and task.owner == 'paused'
                assert task.stopped.is_set() and task.snapshot is None
                assert not task.inflight and not task.uncertain
                denied(task, 'restart_observation', task.observe)
                task.claim_human()
                denied(task, 'restart_recovery', task.recovery_observe)
                denied(task, 'restart_resume',
                       lambda: task.resume('session-budget-diagnostic-restarted', task.epoch))
            task.stop()
            report = {'stage': stage, 'rawCalls': task.used, 'executor_pid': os.getpid(),
                      'sources': sources, 'target_pid': task.pid, 'target_window': task.window,
                      'status': task.control_status(), 'taskStatus': 'UNVERIFIED',
                      'officialModel': False}
            with (directory / ('budget-' + stage + '.json')).open('x') as stream:
                json.dump(report, stream, indent=2)
            print(json.dumps(report))
        finally:
            if not task.stopped.is_set():
                task.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--stage', required=True, choices=('fill', 'restart', 'audit'))
    parser.add_argument('--approve-task', action='store_true')
    args = parser.parse_args()
    run(args.run, args.stage, args.approve_task)
