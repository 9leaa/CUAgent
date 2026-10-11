"""Opt-in selection-only Calc executor; no HTTP/model registration or typing.

Caller supplies trusted window/grid binding and a live lease. Uses the existing
Task ledger and original guest desktop lock; never creates a second budget.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import struct
import time
import zlib

from c0_bridge import Task
from c0_cases import UICase
from calc_targeting import plan_cell_target, confirm_selected_cell
from desktop_lease import LeaseGate
from driver_smoke import Calls, StopRun
from real_app_bridge import require_unlocked

EXECUTABLE = '/Users/mvpagent/Applications/LibreOffice.app/Contents/MacOS/soffice'
SHARED_LOCK = Path('/Users/mvpagent/C0Evidence/bridge.lock')


def _save(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


class CalcSelectionTask(Task):
    RAW_TOOLS = frozenset(('get_window_state', 'click'))
    SIDE_EFFECT_TOOLS = frozenset(('click',))

    def __init__(self, directory, *, lease, pid, window_id, title, cell, grid,
                 approved=False, transport=Calls.cli, identity=None,
                 environment=require_unlocked, shared_lock=SHARED_LOCK):
        if not approved or not isinstance(lease, LeaseGate) or Path(directory).name != lease.run_id:
            raise StopRun('BLOCKED', 'Explicit bound selection approval required')
        if (type(pid) is not int or pid <= 0 or type(window_id) is not int or window_id <= 0
                or not isinstance(title, str) or not title or not isinstance(grid, (list, tuple))):
            raise ValueError('trusted Calc identity and grid required')
        self.lease, self.environment = lease, environment
        environment(); lease.check()
        directory = Path(directory).absolute()
        if directory.parent.resolve(strict=True) != directory.parent:
            raise ValueError('canonical task parent required')
        LeaseGate.private(directory.parent.stat(), directory=True)
        lock = Path(shared_lock).absolute()
        if environment is require_unlocked and lock != SHARED_LOCK:
            raise ValueError('original guest desktop lock required')
        if lock.parent.resolve(strict=True) != lock.parent:
            raise ValueError('canonical shared lock parent required')
        LeaseGate.private(lock.parent.stat(), directory=True)
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        self.lock_fd = fd
        self._permit = None
        self.phase = 'NEW'
        try:
            LeaseGate.private(os.fstat(fd))
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.path.lexists(lock.with_name(lock.name + '.quarantine')):
                raise StopRun('BLOCKED', 'Desktop lock quarantined')
            case = UICase('calc_selection', title, '', (), (), 'org.libreoffice.script', 'LibreOffice', EXECUTABLE)
            super().__init__(Path(directory), transport, identity, approved=approved,
                             case_id='calc_selection', registry={'calc_selection': case})
            self.pid, self.window, self.cell, self.grid = pid, window_id, cell, tuple(grid)
            binding = dict(pid=pid, window_id=window_id, title=title, cell=cell, grid=list(grid))
            path = self.directory / 'selection-binding.json'
            if path.exists() or path.is_symlink():
                if path.is_symlink() or json.loads(path.read_bytes()) != binding:
                    raise StopRun('BLOCKED', 'Original selection binding changed')
            else:
                _save(path, json.dumps(binding).encode())
            self.record(dict(event='selection_scope', operations=['observe','select_once','confirm'],
                             inputPermitted=False))
        except Exception:
            os.close(fd); self.lock_fd = None
            raise

    def _admit(self, tool):
        if tool not in self.RAW_TOOLS or self._permit is None or self._permit[0] != tool:
            raise StopRun('BLOCKED', 'No public raw admission or business result tools')
        try:
            self.environment()
            self.lease.check()
            if self.lock_fd is None:
                raise StopRun('BLOCKED', 'Selection executor closed')
        except Exception:
            self.stop()
            raise
        return super()._admit(tool)

    def _unsupported(self, *args, **kwargs):
        raise StopRun('BLOCKED', 'Selection-only executor; business actions unavailable')

    click = type_text = scroll = write_result = read_result = verify = click_save_panel = _unsupported

    def validate_raw(self, tool, args):
        if self._permit != (tool, args):
            raise StopRun('BLOCKED', 'Only internally planned observation/click allowed')
        super().validate_raw(tool, args)

    def raw(self, tool, args):
        with self.lock:
            return super().raw(tool, args)

    def _call(self, tool, args):
        self._permit = (tool, dict(args))
        try:
            return self.raw(tool, args)
        finally:
            self._permit = None

    def _context(self):
        return dict(pid=self.pid, window_id=self.window, title=self.case.title,
                    observed_at=self.observed_at, now=time.monotonic(), cell=self.cell)

    def observe(self):
        with self.lock:
            self.snapshot = None
            state = self._call('get_window_state', dict(pid=self.pid, window_id=self.window, session=self.run_id))
            try:
                self.observed_at = time.monotonic()
                plan_cell_target(state, **self._context(), grid=self.grid)
                encoded = state.get('screenshot_png_b64')
                if not isinstance(encoded, str) or len(encoded) > 12*1024*1024:
                    raise ValueError('bounded inline PNG required')
                png = base64.b64decode(encoded, validate=True)
                if (len(png) < 33 or len(png) > 8*1024*1024
                        or png[:16] != b'\x89PNG\r\n\x1a\n\0\0\0\rIHDR'
                        or struct.unpack('>II', png[16:24]) != (state['screenshot_width'],state['screenshot_height'])
                        or struct.unpack('>I', png[29:33])[0] != zlib.crc32(png[12:29])):
                    raise ValueError('PNG header and screenshot dimensions must match')
                raw = json.dumps(state, ensure_ascii=False).encode()
                _save(self.directory / ('state-%02d.json' % self.used), raw)
                _save(self.directory / ('state-%02d.png' % self.used), png)
                self.record(dict(event='selection_observation', snapshot_id=state['snapshot_id'],
                                 used=self.used, stateSha256=hashlib.sha256(raw).hexdigest(),
                                 pngSha256=hashlib.sha256(png).hexdigest()))
                self.snapshot = state
                return dict(state=state, png=encoded, used=self.used)
            except Exception:
                self.stop()
                raise

    def select(self, *, point=None):
        with self.lock:
            if self.phase != 'NEW' or self.stopped.is_set() or self.uncertain:
                raise StopRun('BLOCKED', 'Selection already attempted or stopped')
            self.lease.check()
            plan = plan_cell_target(self.snapshot, **self._context(), grid=self.grid, point=point)
            if plan['status'] == 'NEEDS_SCREENSHOT_POINT':
                return plan
            if self.used > 28:
                raise StopRun('BLOCKED', 'Reserve click and post-click observation')
            self.record(dict(event='selection_intent', plan=plan, used=self.used))
            self.phase = 'CLICK_ATTEMPTED'
            self.before_click = plan['snapshot_id']
            self.snapshot = None
            args = dict(pid=self.pid, window_id=self.window, session=self.run_id, **plan['target'])
            try:
                self._call('click', args)
                result = self.observe()
                if result['state']['snapshot_id'] == self.before_click:
                    raise ValueError('post-click snapshot not new')
                self.phase = 'AWAITING_CONFIRMATION'
                return dict(result, status='SELECTION_CONFIRMATION_REQUIRED', inputPermitted=False)
            except Exception:
                self.stop()
                raise

    def confirm(self, *, name_box_index):
        with self.lock:
            if self.phase != 'AWAITING_CONFIRMATION' or self.stopped.is_set() or self.uncertain:
                raise StopRun('BLOCKED', 'Post-click confirmation unavailable')
            try:
                self.lease.check()
                result = confirm_selected_cell(self.snapshot, **self._context(),
                    previous_snapshot_id=self.before_click, name_box_index=name_box_index)
                self.record(dict(event='selection_confirmed', result=result, used=self.used))
                self.phase = 'CONFIRMED'
                return result
            except Exception:
                self.stop()
                raise

    def close(self):
        self.stop()
        with self.dispatch_lock:
            if self.inflight:
                raise StopRun('BLOCKED', 'Retain desktop lock while request is in flight')
            if self.lock_fd is not None:
                os.close(self.lock_fd); self.lock_fd = None
