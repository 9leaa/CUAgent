"""Trusted guest lifecycle; construction never grants permission or runs GUI."""
import fcntl
import hmac
import json
import os
from pathlib import Path
import re
import threading
import time
import stat

from desktop_lease import DesktopTask, LeaseGate
from desktop_tools_http import tools_server
from desktop_app_native import read_identity, request_terminate
from desktop_app_cleanup import ApplicationCleanup, CleanupState
from desktop_evidence import inspect_guest_evidence
from handoff_input import provision


class DesktopGuestRuntime:
    def __init__(self, directory, controller, *, model_token, control_token, shared_lock,
                 port=8766, loopback_test=False, task_factory=DesktopTask):
        self.directory = Path(directory).absolute()
        if (self.directory.resolve(strict=True) != self.directory
                or self.directory.name != controller.gate.run_id):
            raise ValueError('canonical bound run required')
        LeaseGate.private(self.directory.stat(), directory=True)
        for token in (model_token, control_token):
            if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', token):
                raise ValueError('independent credentials required')
        if hmac.compare_digest(model_token, control_token):
            raise ValueError('independent credentials required')
        if type(loopback_test) is not bool or (not loopback_test and task_factory is not DesktopTask):
            raise ValueError('test injection is loopback-only')
        lock_path = Path(shared_lock).absolute()
        if lock_path.parent.resolve(strict=True) != lock_path.parent:
            raise ValueError('canonical shared lock required')
        LeaseGate.private(lock_path.parent.stat(), directory=True)
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            LeaseGate.private(os.fstat(fd))
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.path.lexists(lock_path.with_name(lock_path.name + '.quarantine')):
                raise ValueError('guest shared lock quarantined; manual review required')
        except Exception:
            os.close(fd)
            raise
        self.lock_fd = fd
        self.quarantine = lock_path.with_name(lock_path.name + '.quarantine')
        self.controller = controller
        self.model_token, self.control_token = model_token, control_token
        self.port, self.loopback_test, self.task_factory = port, loopback_test, task_factory
        self.lock = threading.RLock()
        self.task = self.server = self.thread = None
        self.closed = False
        self.application = None

    def capture_application(self, pid, launch_started_us):
        """Trusted launch callback; records ownership, never quits or grants."""
        if self.closed or self.application is not None:
            raise ValueError('application ownership already captured or runtime closed')
        identity = read_identity(pid)
        if (identity is None or type(launch_started_us) is not int
                or not launch_started_us <= identity.started_us <= time.time_ns() // 1000
                or self.closed):
            raise ValueError('new task application identity not confirmed')
        gate = self.controller.gate
        value = {'version': 1, 'runId': gate.run_id, 'owner': gate.owner, 'epoch': gate.epoch,
                 'pid': identity.pid, 'startedUs': identity.started_us,
                 'executable': identity.executable, 'launchStartedUs': launch_started_us}
        fd = os.open(self.directory / 'owned-application.json',
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self.application = identity

    def status(self):
        with self.lock:
            gate = self.controller.gate
            result = {'binding': {'version': 1, 'runId': gate.run_id, 'owner': gate.owner, 'epoch': gate.epoch},
                      'active': self.thread is not None and self.thread.is_alive() and not self.closed,
                      'stopped': self.closed, 'rawCalls': 0, 'pendingCalls': 0,
                      'modelPort': self.server.server_port if self.server is not None else None}
            if self.task is not None:
                with self.task.dispatch_lock:
                    result.update(stopped=self.closed or self.task.stopped.is_set(), rawCalls=self.task.used,
                                  pendingCalls=len(self.task.inflight))
            else:
                lease = self.controller.existing()
                result['stopped'] = self.closed or bool(lease and lease['stopped'])
            return result

    def cleanup_application(self, body):
        """Trusted host has verified its session; guest independently rechecks GUI evidence."""
        with self.lock:
            if (type(body) is not dict or set(body) != {'sessionTerminal', 'sessionVerified', 'hashes'}
                    or body['sessionTerminal'] is not True or body['sessionVerified'] is not True
                    or self.closed or self.task is None or self.application is None):
                raise ValueError('verified original task required')
            task = self.task
            gate = self.controller.gate

            def read_state():
                with task.dispatch_lock:
                    lease = self.controller.existing()
                    stopped = bool(lease and lease.get('stopped') is True and task.stopped.is_set())
                    return CleanupState(gate.run_id, gate.owner, gate.epoch, True, stopped, True,
                                        len(task.inflight), task.uncertain, task.used)

            def read_hashes():
                # Only the fixed task document may be read. Its content serves
                # the guest verifier; equality to the host's approved content
                # is independently enforced via the supplied verified SHA.
                path = self.directory / 'artifacts' / ('handoff-' + gate.run_id + '.txt')
                if path.resolve(strict=True) != path:
                    raise ValueError('document path changed')
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd, 'rb') as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 4096:
                        raise ValueError('document type or size invalid')
                    expected = stream.read(4097)
                report = inspect_guest_evidence(self.directory, run_id=gate.run_id, expected=expected)
                if report['vmStatus'] != 'VERIFIED' or report['rawCalls'] != task.used:
                    raise ValueError('guest verification changed')
                names = {'document': 'artifacts/handoff-' + gate.run_id + '.txt',
                         'result': 'result.txt', 'trace': 'trace.jsonl'}
                return {key: report['files'][name]['sha256'] for key, name in names.items()}

            cleaner = ApplicationCleanup(self.directory, run_id=gate.run_id, owner=gate.owner,
                epoch=gate.epoch, application=self.application, verified_hashes=body['hashes'],
                read_state=read_state, read_identity=read_identity, read_hashes=read_hashes,
                request_terminate=request_terminate)
            return cleaner.run()

    def provision_handoff(self, body):
        return provision(self, body)

    def activate(self):
        with self.lock:
            if self.closed or self.task is not None:
                raise ValueError('activation already attempted or closed')
            if os.path.lexists(self.directory / 'handoff-input-intent.json'):
                raise ValueError('P7 activation not yet enabled; P6 fallback denied')
            try:
                # Even an unconfirmed startup cannot be replayed after restart.
                path = self.directory / 'guest-activation-intent.json'
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'w') as file:
                    json.dump(self.status()['binding'], file)
                    file.flush()
                    os.fsync(file.fileno())
                self.controller.gate.check()
                task_kwargs = {'lease': self.controller.gate, 'approved': True}
                if not self.loopback_test:
                    task_kwargs['launch_observer'] = self.capture_application
                self.task = self.task_factory(self.directory, **task_kwargs)
                self.server = tools_server(self.task, self.model_token, control_token=self.control_token,
                                           port=self.port, loopback_test=self.loopback_test)
                self.thread = threading.Thread(target=self.server.serve_forever,
                                                kwargs={'poll_interval': .05}, daemon=True)
                self.thread.start()
                return self.status()
            except Exception:
                self.revoke()
                if self.server is not None and (self.thread is None or not self.thread.is_alive()):
                    self.server.server_close()
                    self.server = None
                raise

    def revoke(self):
        # No model task.lock acquisition: cancellation must not await transport.
        with self.lock:
            try:
                return self.controller.revoke()
            finally:
                if self.task is not None:
                    self.task.stop()

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.revoke()
            if self.server is not None:
                if self.thread is not None and self.thread.is_alive():
                    self.server.shutdown()
                self.server.server_close()
                if self.thread is not None and self.thread.ident is not None:
                    self.thread.join(3)
            if self.task is not None:
                with self.task.dispatch_lock:
                    if self.task.inflight:
                        if not os.path.lexists(self.quarantine):
                            fd = os.open(self.quarantine, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                            with os.fdopen(fd, 'w') as file:
                                json.dump({'runId': self.controller.gate.run_id,
                                           'reason': 'GUEST_INFLIGHT_REQUIRES_REVIEW'}, file)
                                file.flush()
                                os.fsync(file.fileno())
                        raise RuntimeError('guest in-flight calls require review; shared lock retained')
            self.closed = True
            os.close(self.lock_fd)
