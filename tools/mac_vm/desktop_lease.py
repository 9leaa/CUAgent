"""Guest-local final admission guard. Trusted lease transport is separate."""
import base64
import json
import hashlib
import os
from pathlib import Path
import stat
import time
from driver_smoke import StopRun
from real_app_bridge import RealAppTask


class LeaseGate:
    def __init__(self, path, *, run_id, owner, epoch, clock=time.time):
        if not isinstance(run_id, str) or not run_id or not isinstance(owner, str) or not owner or type(epoch) is not int or epoch < 1:
            raise ValueError('fixed run, owner and positive epoch required')
        self.path = Path(path).absolute()
        self.run_id, self.owner, self.epoch, self.clock = run_id, owner, epoch, clock
        self.last_time = None
        self.denied = False

    def check(self):
        if self.denied:
            raise StopRun('BLOCKED', 'Execution lease previously denied')
        try:
            now = self.clock() * 1000
            if self.last_time is not None and now < self.last_time:
                raise ValueError('clock moved backwards')
            self.last_time = now
            lease = self.read()
            if not (isinstance(lease, dict) and type(lease.get('version')) is int and lease['version'] == 1
                    and lease.get('runId') == self.run_id and lease.get('owner') == self.owner
                    and type(lease.get('epoch')) is int and lease['epoch'] == self.epoch
                    and lease.get('stopped') is False and type(lease.get('expiresAt')) is int
                    and now < lease['expiresAt'] <= now + 30000):
                raise ValueError('invalid execution lease')
        except (OSError, ValueError, TypeError):
            self.denied = True
            raise StopRun('BLOCKED', 'Execution lease unavailable or invalid') from None

    def read(self):
        if self.path.parent.resolve(strict=True) != self.path.parent:
            raise ValueError('control parent symlink')
        directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self.private(os.fstat(directory), directory=True)
            fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(fd, 'rb') as stream:
                self.private(os.fstat(stream.fileno()))
                raw = stream.read(4097)
        finally:
            os.close(directory)
        if len(raw) > 4096:
            raise ValueError('oversized lease')
        return json.loads(raw)

    @staticmethod
    def private(info, directory=False):
        correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        if not correct_type or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('private owner-controlled lease required')


class DesktopTask(RealAppTask):
    """Opt-in extension; existing standalone TextEdit/C0 implementations unchanged."""
    def __init__(self, directory, *args, lease, **kwargs):
        if not isinstance(lease, LeaseGate) or Path(directory).name != lease.run_id:
            raise StopRun('BLOCKED', 'Execution lease run mismatch')
        self.lease = lease
        lease.check()
        super().__init__(directory, *args, **kwargs)

    def observe(self):
        try:
            if self.window is None:
                self._bind_initial_window()
        except Exception:
            self.stop()
            raise
        result = super().observe()
        try:
            files = {}
            for extension in ('json', 'png'):
                path = self.directory / ('state-%02d.' % self.used + extension)
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd, 'rb') as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_size > 8 * 1024 * 1024:
                        raise ValueError('invalid observation file')
                    data = stream.read(8 * 1024 * 1024 + 1)
                    if len(data) != info.st_size:
                        raise ValueError('observation file changed')
                if extension == 'json' and json.loads(data) != result['state']:
                    raise ValueError('observation state mismatch')
                if extension == 'png':
                    if data != base64.b64decode(result['png'], validate=True):
                        raise ValueError('observation image mismatch')
                files[extension] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            self.record({'event': 'observation_evidence', 'snapshot_id': result['state']['snapshot_id'],
                         'used': self.used, 'files': files})
        except Exception:
            self.stop()
            raise
        return result

    def _bind_initial_window(self):
        """One launch, bounded read-only readiness polling of that same PID."""
        self.snapshot = None
        if self.pid is None:
            launched = self.raw('launch_app', self.launch_args)
            if (launched.get('bundle_id') != self.case.bundle
                    or type(launched.get('pid')) is not int or launched['pid'] <= 0):
                raise StopRun('BLOCKED', 'TextEdit launch identity mismatch')
            self.pid = launched['pid']
        deadline = time.monotonic() + 5
        for attempt in range(3):
            if time.monotonic() >= deadline:
                break
            # raw rechecks process identity, VM readiness, lease and budget.
            response = self.raw('list_windows', {'pid': self.pid})
            windows = response.get('windows')
            if (not isinstance(windows, list) or any(not isinstance(w, dict)
                    or type(w.get('pid')) is not int or w['pid'] <= 0
                    or type(w.get('window_id')) is not int or w['window_id'] <= 0
                    or not isinstance(w.get('title'), str) or not isinstance(w.get('app_name'), str)
                    or type(w.get('is_on_screen')) is not bool for w in windows)):
                raise StopRun('UNVERIFIED', 'Invalid TextEdit window inventory')
            candidates = [w for w in windows if w['pid'] == self.pid and w['title'] == self.case.title
                          and w['app_name'] == self.case.app_name and w['is_on_screen'] is True]
            if len(candidates) > 1:
                raise StopRun('UNVERIFIED', 'Ambiguous TextEdit task window')
            if time.monotonic() >= deadline:
                break  # A late response is not timely readiness; do not query again.
            if len(candidates) == 1:
                self.window = candidates[0]['window_id']
                return
            self.record({'event': 'window_readiness_wait', 'attempt': attempt + 1, 'pid': self.pid})
            if attempt < 2:
                time.sleep(min(1, max(0, deadline - time.monotonic())))
        raise StopRun('UNVERIFIED', 'TextEdit task window not ready within bounded observation')

    def _admit(self, tool):
        try:
            self.lease.check()
        except StopRun:
            # Called under the original reentrant dispatch lock; persists across
            # restart even if this denial occurred before the first raw request.
            if not self.stopped.is_set():
                self.stop()
            raise
        return super()._admit(tool)

    def charge_rejection(self, op, prior_used, reason):
        # Even a pre-dispatch refusal consumes the observation's single-action
        # authority. Retain the original budget/audit path, never replay input.
        with self.dispatch_lock:
            self.snapshot = None
            return super().charge_rejection(op, prior_used, reason)
