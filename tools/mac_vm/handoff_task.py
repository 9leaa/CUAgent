"""Opt-in P7 material reader. Not registered in the production P6 protocol."""
import hashlib
import json
import os
import re
import stat

from desktop_lease import DesktopTask, LeaseGate
from driver_smoke import StopRun


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate material key')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('nonfinite material number')


class HandoffDesktopTask(DesktopTask):
    def __init__(self, *args, input_sha256, **kwargs):
        # Trusted constructor binding, never accepted from model tool arguments.
        if not isinstance(input_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', input_sha256):
            raise ValueError('frozen input digest required')
        self.input_sha256 = input_sha256
        super().__init__(*args, **kwargs)

    def read_materials(self):
        with self.lock:
            self.snapshot = None
            with self.dispatch_lock:
                call_id = self.admit('read_materials')
            try:
                value = self._read_frozen_input()
                self.record({'event': 'result', 'tool': 'read_materials', 'call_id': call_id,
                             'value': value, 'inputSha256': self.input_sha256})
                return {'materials': value, 'inputSha256': self.input_sha256, 'used': self.used}
            except Exception as exc:
                self.record({'event': 'error', 'tool': 'read_materials', 'call_id': call_id,
                             'error': type(exc).__name__})
                raise
            finally:
                with self.dispatch_lock:
                    self.inflight.discard(call_id)

    def _read_frozen_input(self):
        directory = self.directory.absolute()
        if directory.resolve(strict=True) != directory:
            raise StopRun('BLOCKED', 'canonical material directory required')
        root = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(root)
            LeaseGate.private(info, directory=True)
            current = directory.stat(follow_symlinks=False)
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise StopRun('BLOCKED', 'material directory changed')
            fd = os.open('handoff-input.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                LeaseGate.private(info)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 < info.st_size <= 256 * 1024:
                    raise StopRun('BLOCKED', 'bounded private material file required')
                raw = stream.read(256 * 1024 + 1)
        finally:
            os.close(root)
        if len(raw) > 256 * 1024 or hashlib.sha256(raw).hexdigest() != self.input_sha256:
            raise StopRun('UNVERIFIED', 'material bytes differ from trusted input')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
        if (type(value) is not dict or set(value) != {'kind', 'project', 'asOf', 'notes', 'tasksCsv', 'previousReport'}
                or value['kind'] != 'project-handoff'):
            raise StopRun('BLOCKED', 'project handoff input required')
        return value
