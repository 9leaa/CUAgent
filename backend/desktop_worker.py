"""Opt-in single-task lifecycle. Harness/VM adapters supply actual execution.

The operator launcher supplies the shared lock, verified adapter and live
admission; a simulator is never a production backend.
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
from backend.desktop_preparation import PreparationClosed


def error_category(error):
    # Never serialize exception text, arguments, class names or traceback.
    if isinstance(error, OSError): return 'OS_ERROR'
    if isinstance(error, (ValueError, TypeError, AssertionError)): return 'VALIDATION_ERROR'
    if isinstance(error, RuntimeError): return 'EXECUTION_ERROR'
    return 'OTHER_ERROR'


@dataclass(frozen=True)
class PreparedDesktop:
    run: Path
    session_id: str
    control_client: object


class DesktopWorker:
    def __init__(self, service, adapter, *, shared_lock, kind='desktop-textedit'):
        if kind not in ('desktop-textedit', 'project-handoff'):
            raise ValueError('UNSUPPORTED_DESKTOP_WORKER_KIND')
        self.kind = kind
        self.service, self.adapter = service, adapter
        self.shared_lock = Path(shared_lock).absolute()
        self.quarantine = self.shared_lock.with_name(self.shared_lock.name + '.quarantine')
        self.owner = str(uuid.uuid4())

    def run_once(self, *, task_id=None, before_claim=None):
        parent = self.shared_lock.parent
        info = parent.stat()
        if (parent.resolve(strict=True) != parent or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid() or info.st_mode & 0o022):
            raise ValueError('owned non-writable canonical shared lock directory required')
        fd = os.open(self.shared_lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+b') as lock:
            info = os.fstat(lock.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('private shared lock required')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.path.lexists(self.quarantine):
                raise RuntimeError('DESKTOP_QUARANTINED_REQUIRES_REVIEW')
            if before_claim is not None:
                if before_claim() is not True:
                    raise RuntimeError('DESKTOP_ADMISSION_REFUSED')
            options = {'task_id': task_id} if task_id is not None else {}
            task = self.service.claim(self.owner, kind=self.kind, **options)
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
        preparation_closed = False
        preparation_guest_not_started = False
        usage = {'available': False}
        phase = 'prepare'
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
                except Exception as error:
                    outcome['heartbeatFailure'] = {'category': error_category(error)}
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
            phase = 'initial-authority'
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
            phase = 'start-session'
            self.adapter.start(prepared)
            deadline = time.monotonic() + 300
            while True:
                phase = 'poll-session-and-guest'
                if lost.is_set() or time.monotonic() >= deadline:
                    raise RuntimeError('DESKTOP_EXECUTION_UNCONFIRMED')
                state = self.adapter.poll(prepared)
                if (type(state.get('terminal')) is not bool or type(state.get('rawCalls')) is not int
                        or not 0 <= state['rawCalls'] <= 30 or type(state.get('pendingCalls')) is not int
                        or state['pendingCalls'] < 0):
                    raise ValueError('INVALID_DESKTOP_OBSERVATION')
                phase = 'record-progress'
                self.service.progress(task.id, self.owner, task.epoch, state['rawCalls'])
                if state['terminal']:
                    terminal = state['pendingCalls'] == 0
                    if not terminal:
                        raise RuntimeError('DESKTOP_INFLIGHT_UNCONFIRMED')
                    break
                done.wait(.2)
            if lost.is_set():
                raise RuntimeError('DESKTOP_AUTHORITY_LOST')
            phase = 'revoke-terminal'
            with phase_lock:
                self.service.desktop_authority(task.id, self.owner, task.epoch)
                renew_guest = False
                closed = control.close()
            if not closed['localRevoked'] or not closed['guestRevoked']:
                raise RuntimeError('DESKTOP_REVOCATION_UNCONFIRMED')
            if callable(getattr(self.adapter, 'usage', None)):
                phase = 'collect-usage'
                usage = self.adapter.usage(prepared)
            try:
                phase = 'verify'
                result = self.adapter.verify(prepared)
            except Exception as error:
                outcome['verificationFailure'] = {'category': error_category(error)}
                phase = 'finish-unverified'
                with phase_lock:
                    done.set()
                    self.service.finish(task.id, self.owner, task.epoch, 'UNVERIFIED',
                        result={'usage': usage}, error_code='DESKTOP_VERIFICATION_FAILED')
                outcome['status'] = 'UNVERIFIED'
            else:
                phase = 'finish-success'
                with phase_lock:
                    if lost.is_set():
                        raise RuntimeError('DESKTOP_AUTHORITY_LOST_DURING_VERIFICATION')
                    done.set()
                    self.service.finish(task.id, self.owner, task.epoch, 'SUCCEEDED', result={**result, 'usage': usage})
                outcome['status'] = 'SUCCEEDED'
        except Exception as error:
            outcome['executionFailure'] = dict(phase=phase, category=error_category(error),
                                               started=started, terminalObserved=terminal,
                                               authorityLost=lost.is_set())
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
            # A pre-error terminal observation alone does not authorize
            # restoration after failed ownership/revocation checks.
            terminal = False
            if (prepared is None and control is None and not started
                    and callable(getattr(self.adapter, 'confirm_prepare_failure', None))):
                try:
                    if thread:
                        thread.join(timeout=8)
                    if lost.is_set() or (thread is not None and thread.is_alive()):
                        raise RuntimeError('DESKTOP_PREPARATION_AUTHORITY_UNCONFIRMED')
                    proof = self.adapter.confirm_prepare_failure(task)
                    if (not isinstance(proof, PreparationClosed)
                            or proof.run != self.service.settings.root / ('p2-' + task.id)
                            or proof.guest_state not in ('closed', 'not-started')
                            or proof.owner != self.owner or type(proof.epoch) is not int or proof.epoch != task.epoch):
                        raise ValueError('DESKTOP_PREPARATION_PROOF_MISMATCH')
                    stopped = self.service.heartbeat(task.id, self.owner, task.epoch, dispatch_stopped=True)
                    if type(stopped) is not bool:
                        raise ValueError('DESKTOP_PREPARATION_STOP_STATE_UNCONFIRMED')
                    status = 'STOPPED' if stopped else 'FAILED'
                    self.service.finish(task.id, self.owner, task.epoch, status,
                        result={'usage': usage}, error_code='DESKTOP_PREPARATION_FAILED')
                    preparation_closed = terminal = True
                    preparation_guest_not_started = proof.guest_state == 'not-started'
                    outcome.update(status=status, errorCode='DESKTOP_PREPARATION_FAILED',
                                   preparationCleanupConfirmed=not preparation_guest_not_started,
                                   guestNotStarted=preparation_guest_not_started,
                                   profileUnchanged=True, appSwitchAttempted=False,
                                   restoreConfirmed=True, restoreRequired=False,
                                   profileSha256=proof.profile_sha256)
                except Exception:
                    pass  # Missing evidence/ownership never releases quarantine.
            if prepared is not None and started and control is not None:
                try:
                    if thread:
                        thread.join(timeout=8)
                    if thread is not None and thread.is_alive():
                        raise RuntimeError('DESKTOP_PULSE_UNCONFIRMED')
                    if self.service.view(task.id)['status'] == 'STOP_REQUESTED':
                        closed = control.close()
                        if not closed['localRevoked'] or not closed['guestRevoked']:
                            raise RuntimeError('DESKTOP_REVOCATION_UNCONFIRMED')
                        deadline = time.monotonic() + 30
                        while True:
                            state = self.adapter.poll(prepared)
                            if (type(state.get('terminal')) is not bool
                                    or state.get('guestStopped') is not True
                                    or type(state.get('pendingCalls')) is not int or state['pendingCalls'] < 0
                                    or type(state.get('rawCalls')) is not int or not 0 <= state['rawCalls'] <= 30):
                                raise RuntimeError('DESKTOP_STOP_OBSERVATION_UNCONFIRMED')
                            if time.monotonic() >= deadline:
                                raise RuntimeError('DESKTOP_STOP_DEADLINE_EXCEEDED')
                            # Refresh DB ownership only; never renew guest dispatch.
                            if self.service.heartbeat(task.id, self.owner, task.epoch, dispatch_stopped=True) is not True:
                                raise RuntimeError('DESKTOP_STOP_REQUEST_MISSING')
                            if state['terminal'] and state['pendingCalls'] == 0:
                                self.service.progress(task.id, self.owner, task.epoch, state['rawCalls'])
                                if callable(getattr(self.adapter, 'usage', None)):
                                    usage = self.adapter.usage(prepared)
                                self.service.finish(task.id, self.owner, task.epoch, 'STOPPED', result={'usage': usage})
                                terminal = True
                                outcome['status'] = 'STOPPED'
                                outcome.pop('errorCode', None)
                                break
                            time.sleep(.2)
                except Exception:
                    pass  # Missing proof retains quarantine and original task.
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
            if preparation_closed:
                closed = {'localRevoked': True, 'guestRevoked': not preparation_guest_not_started,
                          'guestNotStarted': preparation_guest_not_started, 'closed': True,
                          'inflightCancellationConfirmed': False}
            outcome['revocation'] = closed
            outcome['cancelRequested'] = cancelled
            guest_safe = closed['guestRevoked'] or (preparation_closed and preparation_guest_not_started)
            unresolved = (not terminal or not closed['localRevoked'] or not guest_safe
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
