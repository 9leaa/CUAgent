"""Independent single-resource Worker; never a replacement Agent loop."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
from agent.daily_report import dump, prepare, verify
from backend.config import Settings
from backend.db import database
from backend.models import Task
from backend.service import TaskService
from backend.observability import session_usage
from backend.checkpoint import snapshot

PROJECT = Path(__file__).resolve().parents[1]


class Worker:
    def __init__(self, settings):
        self.settings = settings
        self.engine, sessions = database(settings.database_url)
        self.service = TaskService(sessions, settings)
        self.owner = str(uuid.uuid4())

    def rpc_process(self, mode, *paths):
        command = ['node', str(PROJECT / 'agent/harness/daily-report-runner.mjs'), mode, *map(str, paths)]
        # Only observation is retried. Unknown writes/start/activation are never replayed.
        attempts = 3 if mode in ('inspect', 'poll') else 1
        for attempt in range(attempts):
            try:
                result = subprocess.run(command, cwd=PROJECT, env={**os.environ, 'CUAGENT_DSH_COOKIE_FILE': str(self.settings.cookie_file)},
                                        text=True, capture_output=True, timeout=55)
                if result.returncode == 0:
                    return json.loads(result.stdout.strip().splitlines()[-1])
            except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError):
                pass
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
        # Do not leak raw provider failures or credentials to event logs.
        raise RuntimeError('DESKTOP_' + mode.upper() + '_FAILED')

    def prepare_task(self, task):
        root = self.settings.root / 'jobs' / task.id
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        source = root / 'source'
        source.mkdir(mode=0o700, exist_ok=True)
        spec = {'date': task.payload['date'], 'notes': [n['name'] for n in task.payload['notes']],
                'csv': [{'path': c['name'], 'numericColumns': c['numericColumns']} for c in task.payload['csv']]}
        for item in task.payload['notes'] + task.payload['csv']:
            path = source / item['name']
            content = item['content'].encode()
            if path.exists():
                if path.read_bytes() != content or path.is_symlink():
                    raise RuntimeError('SOURCE_SNAPSHOT_CHANGED')
            else:
                with path.open('xb') as file:
                    path.chmod(0o600)
                    file.write(content)
        if not (source / 'spec.json').exists():
            dump(source / 'spec.json', spec)
        elif json.loads((source / 'spec.json').read_text()) != spec:
            raise RuntimeError('SOURCE_SPEC_CHANGED')
        run = root / ('p2-' + task.id)
        if not run.exists():
            prepare(source / 'spec.json', run)
        approval_path = run / 'approval.json'
        if not approval_path.exists():
            raise RuntimeError('PARTIAL_PREPARATION_NEEDS_REVIEW')
        approval = json.loads(approval_path.read_text())
        approval.update(controlPath=str(self.settings.root / 'controls' / (task.id + '.json')), controlEpoch=task.epoch)
        # Approval is developer-owned. Epoch changes never alter ledger identity,
        # session, root, permitted tools or persisted budget.
        temporary = run / ('approval-' + str(task.epoch) + '.tmp')
        dump(temporary, approval)
        os.replace(temporary, approval_path)
        self.service.record_prepared(task.id, self.owner, task.epoch, run, approval['sessionId'])
        return run

    def execute(self, task):
        done, lost, stopping = threading.Event(), threading.Event(), threading.Event()
        heartbeat_errors = []
        def keep_alive():
            while not done.wait(3):
                try:
                    if self.service.heartbeat(task.id, self.owner, task.epoch):
                        stopping.set()
                except Exception:
                    heartbeat_errors.append('LEASE_HEARTBEAT_FAILED')
                    lost.set()
                    return
        thread = threading.Thread(target=keep_alive, daemon=True)
        thread.start()
        run, activated, cancel_sent = None, False, False
        previous_evidence = task.checkpoint['evidence'] if task.checkpoint else None
        def checkpoint(phase):
            nonlocal previous_evidence
            evidence = snapshot(run, previous_evidence)
            self.service.checkpoint(task.id, self.owner, task.epoch, phase, evidence)
            previous_evidence = evidence
        try:
            run = self.prepare_task(task)
            checkpoint('prepared')
            if self.service.heartbeat(task.id, self.owner, task.epoch):
                stopping.set()
            created = (run / 'create-request.json').exists()
            if not created and not stopping.is_set():
                # Config activation is exclusive, with original approved tasks retained.
                config = run / 'active-tasks.json'
                if config.exists():
                    # A prior activation attempt is not repeated blindly.
                    raise RuntimeError('ACTIVATION_ATTEMPT_NEEDS_REVIEW')
                checkpoint('activating')
                self.rpc_process('activate', self.settings.base_tasks, run)
                activated = True
                checkpoint('activated')
                if lost.is_set() or self.service.heartbeat(task.id, self.owner, task.epoch):
                    stopping.set()
                else:
                    checkpoint('starting')
                    self.rpc_process('start', run)
                    created = True
            if not created:
                self.service.finish(task.id, self.owner, task.epoch, 'STOPPED')
                return
            deadline = time.monotonic() + 300
            while True:
                if (stopping.is_set() or lost.is_set() or time.monotonic() > deadline) and not cancel_sent:
                    self.rpc_process('cancel', run)
                    cancel_sent = True
                state = self.rpc_process('poll', run)
                ledger = run / 'audit/calls.jsonl'
                audit = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
                calls = sum(row['event'] == 'dispatch' for row in audit)
                if not lost.is_set():
                    self.service.progress(task.id, self.owner, task.epoch, calls)
                    self.service.import_audit(task.id, self.owner, task.epoch, audit)
                    checkpoint('observing')
                if state['terminal']:
                    break
                if lost.is_set():
                    raise RuntimeError('LEASE_LOST_ORIGINAL_SESSION_NEEDS_REVIEW')
                time.sleep(1)
            if lost.is_set():
                raise RuntimeError('LEASE_LOST_ORIGINAL_SESSION_NEEDS_REVIEW')
            usage = session_usage(run / 'session.jsonl')
            if cancel_sent:
                self.service.finish(task.id, self.owner, task.epoch, 'STOPPED', result={'usage': usage}, error_code='CANCELLED_VERIFY_BEFORE_RESUME')
            else:
                try:
                    checkpoint('verifying')
                    result = verify(run)
                except (ValueError, KeyError, OSError, TypeError, IndexError) as error:
                    # Private report preserves diagnostic detail; public event is a code.
                    dump(run / ('backend-verification-' + uuid.uuid4().hex + '.json'), {'status': 'UNVERIFIED', 'reason': str(error)})
                    self.service.finish(task.id, self.owner, task.epoch, 'UNVERIFIED', result={'usage': usage}, error_code='INDEPENDENT_VERIFICATION_FAILED')
                else:
                    result['usage'] = usage
                    dump(run / ('backend-verification-' + uuid.uuid4().hex + '.json'), result)
                    self.service.finish(task.id, self.owner, task.epoch, 'SUCCEEDED', result=result)
        except Exception as error:
            # Never issue another prompt on an ambiguous RPC failure.
            code = str(error) if str(error).isupper() and len(str(error)) <= 80 else 'WORKER_OPERATION_FAILED'
            if not lost.is_set():
                try:
                    self.service.finish(task.id, self.owner, task.epoch, 'BLOCKED', error_code=code)
                except Exception:
                    pass  # lease expiry remains authoritative; no false terminal claim
            print(json.dumps({'task_id': task.id, 'error_code': code}), flush=True)
        finally:
            done.set()
            thread.join(timeout=5)
            if activated:
                try:
                    self.rpc_process('restore', self.settings.base_tasks)
                except Exception:
                    print(json.dumps({'task_id': task.id, 'error_code': 'RESTORE_PENDING_REQUIRES_IDLE_APP'}), flush=True)

    def run(self, once=False):
        # The resource is this project's single installed Desktop, not a DB/root.
        lock_path = PROJECT / '.runtime/desktop-worker.lock'
        with lock_path.open('a') as lock:
            os.chmod(lock_path, 0o600)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SystemExit('another Worker owns this local desktop resource')
            while True:
                task = self.service.claim(self.owner)
                if task:
                    self.execute(task)
                    print(json.dumps(self.service.view(task.id)), flush=True)
                if once:
                    return
                time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    Worker(Settings.from_env()).run(args.once)
