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
from backend.models import Task, utcnow
from backend.service import TaskService
from backend.observability import session_usage
from backend.checkpoint import snapshot
from backend.recovery import partial_report_plan
from agent.daily_report import sha
from backend.watchdog import observe
from backend.control import write_control

PROJECT = Path(__file__).resolve().parents[1]


class Worker:
    def __init__(self, settings):
        self.settings = settings
        self.engine, sessions = database(settings.database_url)
        self.service = TaskService(sessions, settings)
        self.owner = str(uuid.uuid4())

    def revoke_local(self, task):
        # Losing DB connectivity must not leave the last local permit usable
        # until its expiry. Monotonic epoch/owner checks protect a newer Worker.
        try:
            write_control(self.settings.root / 'controls' / (task.id + '.json'),
                          run_id='p2-' + task.id, epoch=task.epoch, owner=self.owner,
                          expires_at=0, stopped=True)
            return True
        except (OSError, ValueError, KeyError):
            return False

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

    def stop_remote(self, run):
        # A stale poll may hide an already completed turn. Fresh inspection is
        # authoritative; don't resolve/cancel an idle unloaded Agent blindly.
        state = self.rpc_process('inspect', run)
        if not state.get('exists'):
            raise RuntimeError('STOP_SESSION_MISSING_NO_REPLAY')
        issued = not state['terminal']
        if issued:
            self.rpc_process('cancel', run)
        dump(run / ('backend-stop-inspected-' + uuid.uuid4().hex + '.json'),
             {'observation': state, 'cancelIssued': issued})
        return issued

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
        if task.release_at:
            approval['publishNotBefore'] = int(task.release_at.timestamp() * 1000)
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
                    self.revoke_local(task)
                    lost.set()
                    return
        thread = threading.Thread(target=keep_alive, daemon=True)
        thread.start()
        run, activated, cancel_sent = None, False, False
        previous_evidence = task.checkpoint['evidence'] if task.checkpoint else None
        business_progress = task.checkpoint.get('businessProgress') if task.checkpoint else None
        def checkpoint(phase):
            nonlocal previous_evidence
            evidence = snapshot(run, previous_evidence)
            self.service.checkpoint(task.id, self.owner, task.epoch, phase, evidence, business_progress=business_progress)
            previous_evidence = evidence
        try:
            run = self.prepare_task(task)
            # A previous Worker can die after activating this task's profile.
            # Recovery owns the same project-wide lock and must also restore it.
            activated = (run / 'active-tasks.json').exists()
            checkpoint('prepared')
            if self.service.heartbeat(task.id, self.owner, task.epoch):
                stopping.set()
            created = (run / 'create-request.json').exists()
            if created and (run / 'prompt-request.json').exists():
                state = self.rpc_process('inspect', run)
                dump(run / ('backend-reconciled-' + uuid.uuid4().hex + '.json'), state)
                if not state['exists']:
                    raise RuntimeError('ORIGINAL_SESSION_MISSING_NO_REPLAY')
                if not state['running'] and not state['promptObserved']:
                    # Disk absence cannot rule out a lost live-inbox request.
                    raise RuntimeError('PROMPT_ACCEPTANCE_UNKNOWN_NO_REPLAY')
                if state['terminal'] and not (run / 'continuation-request.json').exists() and not stopping.is_set():
                    self.rpc_process('poll', run)
                    try:
                        verify(run)
                    except (ValueError, KeyError, OSError, TypeError, IndexError):
                        plan = partial_report_plan(run, previous_evidence)
                        if task.release_at and task.release_at > utcnow():
                            checkpoint('verifying')
                            self.service.wait_for_release(task.id, self.owner, task.epoch, usage=session_usage(run / 'session.jsonl'))
                            return
                        plan['sourceSessionSha256'] = sha((run / 'session.jsonl').read_bytes())
                        plan_path = run / 'continuation-plan.json'
                        if plan_path.exists():
                            if json.loads(plan_path.read_text()) != plan:
                                raise RuntimeError('CONTINUATION_PLAN_CHANGED')
                        else:
                            dump(plan_path, plan)
                        self.rpc_process('rebind', self.settings.base_tasks, run)
                        activated = True
                        if lost.is_set() or self.service.heartbeat(task.id, self.owner, task.epoch):
                            stopping.set()
                        else:
                            checkpoint('starting')
                            accepted = self.rpc_process('continue', run)
                            if not accepted.get('accepted'):
                                raise RuntimeError('CONTINUATION_NOT_ACCEPTED')
                            # A confirmed new business step ends the deliberate
                            # release wait; an unchanged heartbeat never does.
                            business_progress = None
            if created and not (run / 'prompt-request.json').exists() and not stopping.is_set():
                state = self.rpc_process('inspect', run)
                if not state['exists'] or state['running'] or state['userMessages'] or state['calls'] or state['terminal']:
                    raise RuntimeError('ORIGINAL_SESSION_NOT_PROVEN_UNSTARTED')
                # Load the newly acquired epoch before permitting the first prompt.
                self.rpc_process('rebind', self.settings.base_tasks, run)
                activated = True
                if lost.is_set() or self.service.heartbeat(task.id, self.owner, task.epoch):
                    stopping.set()
                else:
                    checkpoint('starting')
                    self.rpc_process('start-existing', run)
                if stopping.is_set():
                    self.service.finish(task.id, self.owner, task.epoch, 'STOPPED')
                    return
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
            cancellation_deadline = None
            cancellation_reason = 'CANCELLED_VERIFY_BEFORE_RESUME'
            while True:
                if (stopping.is_set() or lost.is_set()) and not cancel_sent:
                    self.stop_remote(run)
                    cancel_sent = True
                    cancellation_deadline = time.monotonic() + 30
                state = self.rpc_process('poll', run)
                ledger = run / 'audit/calls.jsonl'
                audit = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
                calls = sum(row['event'] == 'dispatch' for row in audit)
                business_progress = observe(business_progress, [state['userMessages'], calls,
                    sum(row['event'] == 'result' for row in audit)])
                if not lost.is_set():
                    self.service.progress(task.id, self.owner, task.epoch, calls)
                    self.service.import_audit(task.id, self.owner, task.epoch, audit)
                    checkpoint('observing')
                if state['terminal']:
                    break
                if business_progress['stalled'] and not cancel_sent and not lost.is_set():
                    self.service.stop(task.id)
                    cancellation_reason = 'NO_BUSINESS_PROGRESS'
                    stopping.set()
                if cancellation_deadline is not None and time.monotonic() > cancellation_deadline:
                    raise RuntimeError('CANCEL_TERMINATION_UNKNOWN_NO_REPLAY')
                if lost.is_set():
                    raise RuntimeError('LEASE_LOST_ORIGINAL_SESSION_NEEDS_REVIEW')
                time.sleep(1)
            if lost.is_set():
                raise RuntimeError('LEASE_LOST_ORIGINAL_SESSION_NEEDS_REVIEW')
            continuing = (run / 'continuation-request.json').exists()
            usage = session_usage(run / ('session-continuation.jsonl' if continuing else 'session.jsonl'))
            if task.release_at and not continuing and not cancel_sent:
                plan = partial_report_plan(run, previous_evidence)
                if plan['missing'] != ['report.md']:
                    raise RuntimeError('SCHEDULED_DRAFT_PUBLISHED_UNEXPECTEDLY')
                checkpoint('verifying')
                self.service.wait_for_release(task.id, self.owner, task.epoch, usage=usage)
                return
            if cancel_sent:
                self.service.finish(task.id, self.owner, task.epoch, 'STOPPED', result={'usage': usage}, error_code=cancellation_reason)
            else:
                try:
                    checkpoint('verifying')
                    result = verify(run, continuation=continuing)
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
            self.revoke_local(task)
            code = str(error) if str(error).isupper() and len(str(error)) <= 80 else 'WORKER_OPERATION_FAILED'
            if not lost.is_set():
                try:
                    failed_usage = None
                    if run:
                        source = run / ('session-continuation.jsonl' if (run / 'session-continuation.jsonl').exists() else 'session.jsonl')
                        if source.exists():
                            try:
                                failed_usage = {'usage': session_usage(source)}
                            except (OSError, ValueError, KeyError, TypeError):
                                pass
                    self.service.finish(task.id, self.owner, task.epoch, 'BLOCKED', error_code=code, result=failed_usage)
                except Exception:
                    pass  # lease expiry remains authoritative; no false terminal claim
            print(json.dumps({'task_id': task.id, 'error_code': code}), flush=True)
        finally:
            done.set()
            thread.join(timeout=5)
            if activated:
                try:
                    restored = self.rpc_process('restore', self.settings.base_tasks)
                    dump(run / ('backend-restored-' + uuid.uuid4().hex + '.json'), restored)
                except Exception:
                    dump(run / ('backend-restore-pending-' + uuid.uuid4().hex + '.json'),
                         {'error_code': 'RESTORE_PENDING_REQUIRES_IDLE_APP'})
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
