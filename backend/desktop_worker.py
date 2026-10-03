"""Opt-in single-task lifecycle. Harness/VM adapters supply actual execution.

No production launcher: shared lock, verified adapter and deployment cutover
must be supplied explicitly; a simulator is never a production backend.
"""
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import stat
import threading
import time
import uuid
from backend.desktop_execution_control import DesktopExecutionControl


@dataclass(frozen=True)
class PreparedDesktop:
    run: Path
    session_id: str
    control_client: object


class DesktopWorker:
    def __init__(self, service, adapter, *, shared_lock):
        self.service, self.adapter = service, adapter
        self.shared_lock = Path(shared_lock).absolute()
        self.quarantine = self.shared_lock.with_name(self.shared_lock.name + '.quarantine')
        self.owner = str(uuid.uuid4())

    def run_once(self):
        parent = self.shared_lock.parent
        if parent.resolve(strict=True) != parent or parent.stat().st_mode & 0o077:
            raise ValueError('private canonical shared lock directory required')
        fd = os.open(self.shared_lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+b') as lock:
            info = os.fstat(lock.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('private shared lock required')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.path.lexists(self.quarantine):
                raise RuntimeError('DESKTOP_QUARANTINED_REQUIRES_REVIEW')
            task = self.service.claim(self.owner, kind='desktop-textedit')
            if task is None:
                return None
            return self.execute(task)

    def execute(self, task):
        done, lost = threading.Event(), threading.Event()
        phase_lock = threading.RLock()
        renew_guest = True
        prepared = control = thread = None
        started = terminal = False
        cancelled = False
        usage = {'available': False}
        outcome = {'taskId': task.id, 'status': 'BLOCKED', 'quarantined': False,
                   'restoreConfirmed': False}
        def pulse():
            while not done.wait(3):
                try:
                    with phase_lock:
                        if control is not None and renew_guest:
                            control.refresh()
                        elif self.service.heartbeat(task.id, self.owner, task.epoch, dispatch_stopped=not renew_guest):
                            raise RuntimeError('DESKTOP_STOP_REQUESTED')
                except Exception:
                    lost.set()
                    return
        try:
            thread = threading.Thread(target=pulse, daemon=True)
            thread.start()
            prepared = self.adapter.prepare(task)
            if (not isinstance(prepared, PreparedDesktop) or not prepared.session_id
                    or prepared.run.is_symlink() or not prepared.run.is_dir()
                    or not prepared.run.resolve().is_relative_to(self.service.settings.root)):
                raise ValueError('INVALID_PREPARED_DESKTOP')
            self.service.record_prepared(task.id, self.owner, task.epoch, prepared.run, prepared.session_id)
            control = DesktopExecutionControl(self.service, prepared.control_client,
                task_id=task.id, owner=self.owner, epoch=task.epoch)
            if lost.is_set():
                raise RuntimeError('DESKTOP_AUTHORITY_LOST_DURING_PREPARE')
            control.refresh()
            with (prepared.run / 'desktop-start-intent.json').open('x') as file:
                os.chmod(file.name, 0o600)
                json.dump({'taskId': task.id, 'sessionId': prepared.session_id,
                           'owner': self.owner, 'epoch': task.epoch}, file)
                file.flush(); os.fsync(file.fileno())
            started = True  # Persisted adapter intent must precede its real RPC.
            self.adapter.start(prepared)
            deadline = time.monotonic() + 300
            while True:
                if lost.is_set() or time.monotonic() >= deadline:
                    raise RuntimeError('DESKTOP_EXECUTION_UNCONFIRMED')
                state = self.adapter.poll(prepared)
                if (type(state.get('terminal')) is not bool or type(state.get('rawCalls')) is not int
                        or not 0 <= state['rawCalls'] <= 30 or type(state.get('pendingCalls')) is not int
                        or state['pendingCalls'] < 0):
                    raise ValueError('INVALID_DESKTOP_OBSERVATION')
                self.service.progress(task.id, self.owner, task.epoch, state['rawCalls'])
                if state['terminal']:
                    terminal = state['pendingCalls'] == 0
                    if not terminal:
                        raise RuntimeError('DESKTOP_INFLIGHT_UNCONFIRMED')
                    break
                done.wait(.2)
            if lost.is_set():
                raise RuntimeError('DESKTOP_AUTHORITY_LOST')
            with phase_lock:
                self.service.desktop_authority(task.id, self.owner, task.epoch)
                renew_guest = False
                closed = control.close()
            if not closed['localRevoked'] or not closed['guestRevoked']:
                raise RuntimeError('DESKTOP_REVOCATION_UNCONFIRMED')
            if callable(getattr(self.adapter, 'usage', None)):
                usage = self.adapter.usage(prepared)
            try:
                result = self.adapter.verify(prepared)
            except Exception:
                with phase_lock:
                    done.set()
                    self.service.finish(task.id, self.owner, task.epoch, 'UNVERIFIED',
                        result={'usage': usage}, error_code='DESKTOP_VERIFICATION_FAILED')
                outcome['status'] = 'UNVERIFIED'
            else:
                with phase_lock:
                    if lost.is_set():
                        raise RuntimeError('DESKTOP_AUTHORITY_LOST_DURING_VERIFICATION')
                    done.set()
                    self.service.finish(task.id, self.owner, task.epoch, 'SUCCEEDED', result={**result, 'usage': usage})
                outcome['status'] = 'SUCCEEDED'
        except Exception:
            outcome['errorCode'] = 'DESKTOP_EXECUTION_REQUIRES_REVIEW'
            done.set()
            if control:
                control.close()  # Stop new dispatch before requesting cancellation.
            if prepared is not None and started and not terminal:
                try:
                    self.adapter.cancel(prepared)
                    cancelled = True
                except Exception:
                    pass
        finally:
            done.set()
            if prepared is not None and callable(getattr(self.adapter, 'usage', None)):
                try:
                    usage = self.adapter.usage(prepared)
                except Exception:
                    pass  # Accounting must not prevent revocation or quarantine.
            outcome['usage'] = usage
            if thread:
                thread.join(timeout=8)
            closed = control.close() if control else {'localRevoked': False, 'guestRevoked': False}
            outcome['revocation'] = closed
            outcome['cancelRequested'] = cancelled
            unresolved = (not terminal or not closed['localRevoked'] or not closed['guestRevoked']
                          or (thread is not None and thread.is_alive()))
            if unresolved or outcome['status'] == 'BLOCKED':
                outcome['quarantined'] = True
                with self.quarantine.open('x') as file:
                    self.quarantine.chmod(0o600)
                    json.dump({'taskId': task.id, 'reason': 'DESKTOP_EXECUTION_REQUIRES_REVIEW'}, file)
            if prepared is not None and terminal and not unresolved:
                try:
                    self.adapter.restore(prepared)
                    outcome['restoreConfirmed'] = True
                except Exception:
                    outcome['restoreError'] = 'RESTORE_PENDING_REQUIRES_REVIEW'
                    if not outcome['quarantined']:
                        outcome['quarantined'] = True
                        with self.quarantine.open('x') as file:
                            self.quarantine.chmod(0o600)
                            json.dump({'taskId': task.id, 'reason': 'RESTORE_PENDING_REQUIRES_REVIEW'}, file)
            with (self.service.settings.root / ('desktop-outcome-' + uuid.uuid4().hex + '.json')).open('x') as file:
                os.chmod(file.name, 0o600)
                json.dump(outcome, file)
        return outcome
