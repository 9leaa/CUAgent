"""Trusted guest lifecycle; construction never grants permission or runs GUI."""
import fcntl
import hmac
import json
import os
from pathlib import Path
import re
import threading

from desktop_lease import DesktopTask, LeaseGate
from desktop_tools_http import tools_server


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
        except Exception:
            os.close(fd)
            raise
        self.lock_fd = fd
        self.controller = controller
        self.model_token, self.control_token = model_token, control_token
        self.port, self.loopback_test, self.task_factory = port, loopback_test, task_factory
        self.lock = threading.RLock()
        self.task = self.server = self.thread = None
        self.closed = False

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

    def activate(self):
        with self.lock:
            if self.closed or self.task is not None:
                raise ValueError('activation already attempted or closed')
            try:
                # Even an unconfirmed startup cannot be replayed after restart.
                path = self.directory / 'guest-activation-intent.json'
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'w') as file:
                    json.dump(self.status()['binding'], file)
                    file.flush()
                    os.fsync(file.fileno())
                self.controller.gate.check()
                self.task = self.task_factory(self.directory, lease=self.controller.gate, approved=True)
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
                        raise RuntimeError('guest in-flight calls require review; shared lock retained')
            self.closed = True
            os.close(self.lock_fd)
