"""Guest-local final admission guard. Trusted lease transport is separate."""
import json
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
