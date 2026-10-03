"""Run exactly one frozen P4 pair. Operator must check quota between invocations."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from agent.daily_report import dump, require, sha, verify
from agent.efficiency import compare
from agent.efficiency_evidence import extract
from agent.efficiency_suite import PROJECT, check
from backend.control import write_control


def rpc(mode, *paths):
    command = ['node', str(PROJECT / 'agent/harness/daily-report-runner.mjs'), mode, *map(str, paths)]
    result = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True, timeout=180)
    # Do not expose account data or subprocess diagnostics through the public summary.
    if result.returncode:
        raise RuntimeError('desktop command failed: ' + mode + '; original intents must be reconciled')
    return json.loads(result.stdout.strip().splitlines()[-1])


def collect_trial(trial):
    run = Path(trial['runDir'])
    request = json.loads((run / 'prompt-request.json').read_text())['request']
    require(request['sessionId'] == trial['sessionId'] and len(request['content']) == 1 and
            request['content'][0]['type'] == 'text' and sha(request['content'][0]['text']) == trial['promptSha256'],
            'actual prompt differs from frozen prompt')
    rows = [json.loads(line) for line in (run / 'session.jsonl').read_text().splitlines() if line]
    users = [r['data'] for r in rows if r['type'] == 'user/message']
    require(len(users) == 1 and users[0]['source']['rpcId'] == request['requestId'] and
            users[0]['content'] == request['content'], 'original session prompt mismatch')
    evidence = extract(run)
    try:
        verdict = verify(run, aggregate=trial['arm'] == 'candidate')
    except (ValueError, KeyError, OSError, TypeError, IndexError) as error:
        verdict = {'status': 'UNVERIFIED', 'reason': str(error)}
    succeeded = verdict['status'] == 'SUCCEEDED'
    # A failed business verifier is not automatically a safety pass: require a later audit.
    safety = False if evidence['safetyIssues'] else True if succeeded else None
    return {**trial, 'status': 'SUCCEEDED' if succeeded else 'UNVERIFIED', 'verified': succeeded,
            'safetyPassed': safety, 'attempts': [evidence['attempt']], 'evidence': evidence}


def execute_trial(trial, base, call=rpc):
    run = Path(trial['runDir'])
    approval = json.loads((run / 'approval.json').read_text())
    require(not any((run / name).exists() for name in ('lifecycle-start.json', 'create-request.json',
            'prompt-request.json', 'session.jsonl')), 'trial already attempted; no replacement or replay')
    require(approval.get('controlEpoch') == 1 and approval.get('controlPath') == str(run / 'control.json'),
            'frozen execution control required')
    owner = approval['sessionId']
    def lease(stopped=False):
        write_control(approval['controlPath'], run_id=approval['runId'], epoch=1, owner=owner,
                      expires_at=time.time() * 1000 + 30000, stopped=stopped)
    tasks = json.loads(Path(base).read_text())['tasks']
    def hashes():
        return {t['ledgerPath']: sha(Path(t['ledgerPath']).read_bytes()) for t in tasks}
    before = hashes()
    start = time.monotonic_ns()
    dump(run / 'lifecycle-start.json', dict(runId=approval['runId'], sessionId=owner,
         startedMonotonicNs=start, baseLedgerHashes=before))
    interventions, failure = [], None
    terminal, restored = False, False
    verdict = None
    try:
        lease()
        call('activate', base, run)
        lease()
        require(call('start', run).get('accepted') is True, 'prompt not acknowledged; never replay')
        deadline = time.monotonic() + 180
        while True:
            lease()
            state = call('poll', run)
            if state.get('terminal'):
                terminal = True
                break
            require(time.monotonic() < deadline, 'trial deadline exceeded')
            time.sleep(1)
        try:
            verdict = verify(run, aggregate=trial['arm'] == 'candidate')
        except (ValueError, KeyError, OSError, TypeError, IndexError) as error:
            verdict = {'status': 'UNVERIFIED', 'reason': str(error)}
        dump(run / 'business-verification.json', verdict)
    except Exception as error:
        failure = type(error).__name__ + ': ' + str(error)
        interventions.append({'kind': 'execution-error', 'monotonicNs': time.monotonic_ns()})
    finally:
        lease(stopped=True)
        if not terminal:
            # Reconcile original identity; cancellation does not authorize another prompt.
            try:
                state = call('inspect', run)
                if state.get('exists') and not state.get('terminal'):
                    interventions.append({'kind': 'cancel', 'monotonicNs': time.monotonic_ns()})
                    call('cancel', run)
                if state.get('exists'):
                    deadline = time.monotonic() + 60
                    while True:
                        state = call('poll', run)
                        if state.get('terminal'):
                            terminal = True
                            break
                        require(time.monotonic() < deadline, 'original session remains nonterminal')
                        time.sleep(1)
            except Exception as error:
                failure = (failure or '') + '; reconciliation: ' + type(error).__name__
        try:
            call('restore', base)
            require(hashes() == before, 'base ledgers changed')
            restored = True
        except Exception as error:
            failure = (failure or '') + '; restoration: ' + type(error).__name__
        end = time.monotonic_ns()
        lifecycle = dict(version=1, runId=approval['runId'], sessionId=owner,
                         startedMonotonicNs=start, endedMonotonicNs=end,
                         boundary='before-activate-through-after-restore', interventions=interventions,
                         complete=terminal and restored, restored=restored, failure=failure)
        for name, file in [('sessionSha256', run / 'session.jsonl'),
                           ('auditSha256', Path(approval['ledgerPath']))]:
            if file.exists(): lifecycle[name] = sha(file.read_bytes())
        dump(run / 'lifecycle.json', lifecycle)
    require(lifecycle['complete'], 'incomplete lifecycle; preserve original trial and stop')
    result = collect_trial(trial)
    dump(run / 'efficiency-result.json', result)
    return result


def run_pair(directory, quota_file):
    from backend.manage import load_env
    from backend.config import Settings
    from backend.db import database
    from backend.models import Task
    from sqlalchemy import select
    os.environ.update(load_env())
    settings = Settings.from_env()
    root = Path(directory).resolve()
    check(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    quota = json.loads(Path(quota_file).read_text())
    require(quota.get('ordinaryUsageAllowed') is True and type(quota.get('remainingPercent')) in (int, float)
            and quota['remainingPercent'] > 5 and quota.get('creditsBalance') == '62494.0260570000'
            and quota.get('resetCardsUsed') == 0 and type(quota.get('checkedAt')) in (int, float)
            and 0 <= time.time() - quota['checkedAt'] < 300, 'fresh operator quota check required')
    with (PROJECT / '.runtime/desktop-worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _, sessions = database(settings.database_url)
        with sessions() as db:
            require(not list(db.scalars(select(Task.id).where(Task.status.in_(
                    ['QUEUED', 'RUNNING', 'WAITING_RELEASE'])))), 'backend queue must be idle')
        results = []
        next_index = None
        for trial in manifest['trials']:
            file = Path(trial['runDir']) / 'efficiency-result.json'
            if file.exists():
                require(next_index is None, 'non-prefix results; do not skip original trials')
                original = json.loads(file.read_text())
                require(collect_trial(trial) == original, 'prior trial evidence changed')
                results.append(original)
            elif next_index is None:
                next_index = trial['index']
        require(next_index is not None, 'all trials already collected')
        require(len(results) % 2 == 0, 'partial pair requires original-evidence reconciliation')
        dump(root / f'quota-before-pair-{next_index:02d}.json', quota)
        for trial in [t for t in manifest['trials'] if t['index'] == next_index]:
            check(root)
            result = execute_trial(trial, settings.base_tasks)
            results.append(result)
            print(json.dumps({'index': next_index, 'arm': trial['arm'], 'status': result['status']}), flush=True)
        summary = compare(manifest, results)
        dump(root / f'comparison-after-pair-{next_index:02d}.json', summary)
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--quota-record', required=True)
    args = parser.parse_args()
    print(json.dumps(run_pair(args.directory, args.quota_record)))
