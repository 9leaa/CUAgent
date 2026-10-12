"""M1 fixed Calculator workflow. No model, arbitrary shell or general tool router.

Conceptual reference: UFO be75a7d ufo/module/dispatcher.py; no copied code.
Timeouts on actions remain UNKNOWN; they are never replayed.
"""
import ctypes
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import stat
import sys
import time
import uuid

DRIVER = '/Applications/CuaDriver.app/Contents/MacOS/cua-driver'
CALCULATOR = '/System/Applications/Calculator.app/Contents/MacOS/Calculator'
BUNDLE = 'com.apple.calculator'
BUTTONS = ('All Clear', '1', '2', 'Multiply', '3', '4', 'Equals')


class StopRun(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class DriverCallError(StopRun):
    """Bounded private evidence, never a model-facing error message."""
    def __init__(self, reason, *, returncode=None, stdout=None, stderr=None):
        super().__init__('FAILED' if reason=='nonzero_exit' else 'UNVERIFIED',
                         'Driver call failed: ' + reason)
        def stream(value):
            raw = value if isinstance(value, bytes) else (value or '').encode('utf-8', errors='replace')
            return dict(preview=raw[:4096].decode('utf-8', errors='replace'),
                        bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                        truncated=len(raw)>4096)
        self.diagnostic = dict(reason=reason, returncode=returncode,
                               stdout=stream(stdout), stderr=stream(stderr))


def require_vm():
    if sys.platform != 'darwin' or getpass.getuser() != 'mvpagent' or os.geteuid() == 0:
        raise StopRun('BLOCKED', 'Requires the ordinary mvpagent account inside the test VM')
    model = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'], text=True).strip()
    if not model.startswith('VirtualMac'):
        raise StopRun('BLOCKED', 'Refusing to operate a host Mac')


def calculator_identity(pid):
    if type(pid) is not int or pid <= 0:
        raise StopRun('BLOCKED', 'Invalid calculator PID')
    lib = ctypes.CDLL('/usr/lib/libproc.dylib')
    lib.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    lib.proc_pidpath.restype = ctypes.c_int
    buf = ctypes.create_string_buffer(4096)
    if lib.proc_pidpath(pid, buf, len(buf)) <= 0 or os.fsdecode(buf.value) != CALCULATOR:
        raise StopRun('BLOCKED', 'PID no longer belongs to the system Calculator')


def display_value(state):
    """Read AXStaticText from the window subtree, never buttons or menu labels."""
    tree = state.get('tree_markdown', '')
    window = tree.split('\n- ', 1)[0]
    values = []
    for text in re.findall(r'^\s+- AXStaticText = "([^"\n]+)"\s*$', window, re.M):
        clean = text.translate({ord(c): None for c in '\u200e\u200f\u2066\u2067\u2068\u2069'})
        clean = clean.replace('\u2212', '-')
        if re.fullmatch(r'-?(?:[0-9]+|[1-9][0-9]{0,2}(?:,[0-9]{3})+)', clean):
            values.append(clean.replace(',', ''))
    if len(values) != 1:
        raise StopRun('UNVERIFIED', 'No unique integer display in fresh Calculator AX state')
    return values[0]


def button_in_window(state, label):
    roots = {e['element_index'] for e in state.get('elements', [])
             if e.get('role') == 'AXWindow' and e.get('label') == 'Calculator'}
    found = [e for e in state.get('elements', []) if e.get('role') == 'AXButton'
             and e.get('label') == label and e.get('parent_index') in roots
             and e.get('enabled') is True and 'AXPress' in e.get('actions', [])]
    if len(found) != 1 or label not in BUTTONS:
        raise StopRun('BLOCKED', 'Missing or ambiguous permitted Calculator button: ' + label)
    return found[0]


class Calls:
    def __init__(self, directory, transport=None, identity=calculator_identity):
        self.directory = directory
        self.run_id = directory.name
        self.count = 0
        self.pid = None
        self.window_id = None
        self.transport = transport or self.cli
        self.identity = identity
        self.log = (directory / 'trace.jsonl').open('x', encoding='utf-8')

    @staticmethod
    def cli(tool, args):
        return Calls._cli([DRIVER], tool, args)

    @staticmethod
    def _cli(command, tool, args):
        try:
            result = subprocess.run([*command, tool, json.dumps(args)], capture_output=True,
                                    text=True, timeout=35,
                                    env=dict(os.environ, CUA_DRIVER_RS_TELEMETRY_ENABLED='false'))
        except subprocess.TimeoutExpired as exc:
            raise DriverCallError('timeout', stdout=exc.stdout, stderr=exc.stderr) from exc
        if result.returncode:
            raise DriverCallError('nonzero_exit', returncode=result.returncode,
                                  stdout=result.stdout, stderr=result.stderr)
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise DriverCallError('invalid_json', returncode=result.returncode,
                                  stdout=result.stdout, stderr=result.stderr) from e
        if not isinstance(value, dict):
            raise DriverCallError('invalid_shape', returncode=result.returncode,
                                  stdout=result.stdout, stderr=result.stderr)
        return value

    def record(self, row):
        self.log.write(json.dumps(row, ensure_ascii=False) + '\n')
        self.log.flush()
        os.fsync(self.log.fileno())

    def invoke(self, tool, args, *, button=None):
        if self.count >= 30:
            raise StopRun('FAILED', 'Tool budget exhausted; no further observations permitted')
        if tool == 'launch_app':
            valid = self.pid is None and args == {'bundle_id': BUNDLE}
        elif tool == 'list_windows':
            valid = args == {'pid': self.pid} and self.pid is not None
        elif tool == 'get_window_state':
            valid = (set(args) == {'pid', 'window_id', 'session', 'screenshot_out_file'}
                     and args.get('pid') == self.pid and args.get('window_id') == self.window_id
                     and args.get('session') == self.run_id
                     and Path(args['screenshot_out_file']).parent == self.directory
                     and not Path(args['screenshot_out_file']).exists())
        elif tool == 'click':
            valid = (button is not None and button.get('label') in BUTTONS
                     and args == {'pid': self.pid, 'window_id': self.window_id,
                                  'session': self.run_id,
                                  'element_index': button['element_index'],
                                  'element_token': button['element_token']})
        else:
            valid = False
        if not valid:
            raise StopRun('BLOCKED', 'Tool or arguments outside the fixed M1 policy')
        if self.pid is not None:
            self.identity(self.pid)
        self.count += 1
        row = dict(run_id=self.run_id, step_id=self.count, call_id=str(uuid.uuid4()),
                   tool=tool, args=args, button_label=button.get('label') if button else None,
                   status='DISPATCHED', result=None, error=None, duration_ms=None,
                   evidence_path=args.get('screenshot_out_file'))
        self.record(row)
        start = time.monotonic()
        try:
            value = self.transport(tool, args)
            row.update(status='RETURNED', result=value)
            return value
        except subprocess.TimeoutExpired as e:
            row.update(status='UNKNOWN' if tool in ('click', 'launch_app') else 'FAILED',
                       error='Driver call timed out; no automatic retry')
            raise StopRun('UNVERIFIED' if row['status'] == 'UNKNOWN' else 'FAILED', row['error']) from e
        except StopRun as e:
            row.update(status=e.status, error=str(e))
            raise
        finally:
            row['duration_ms'] = round((time.monotonic() - start) * 1000, 3)
            self.record(row)

    def observe(self):
        state = self.invoke('get_window_state', {
            'pid': self.pid, 'window_id': self.window_id, 'session': self.run_id,
            'screenshot_out_file': str(self.directory / f'state-{self.count + 1:02d}.png')})
        if (state.get('pid') != self.pid or state.get('window_id') != self.window_id
                or state.get('app_name') != 'Calculator' or state.get('window_title') != 'Calculator'
                or not state.get('snapshot_id') or state.get('degraded_reason')
                or not state.get('screenshot_frame_valid')):
            raise StopRun('UNVERIFIED', 'Calculator identity or usable observation not established')
        # This Driver version always reports elements_complete=false: only
        # actionable nodes are indexed. Require positive button/display evidence
        # below; never interpret an absent node as proof it does not exist.
        return state


DIAGNOSTIC_SHA256 = '1c86beeaaf07d0deb43fa232961606ea8984ca1202e7e3e102e6c924ac6a2104'
DIAGNOSTIC_DRIVER = '/Users/mvpagent/CUAgentDriverDiagnostic-' + DIAGNOSTIC_SHA256 + '/cua-driver'
DIAGNOSTIC_SOCKET = '/Users/mvpagent/Library/Caches/cua-driver/cua-driver.sock'


def diagnostic_cli_binding():
    return dict(path=DIAGNOSTIC_DRIVER, sha256=DIAGNOSTIC_SHA256, socket=DIAGNOSTIC_SOCKET)


def diagnostic_cli(tool, args):
    """Trusted opt-in transport only; Task still owns authorization and accounting."""
    require_vm()
    path = Path(DIAGNOSTIC_DRIVER)
    parent = path.parent
    if parent.resolve(strict=True) != parent:
        raise StopRun('BLOCKED', 'Diagnostic CLI parent is not canonical')
    info = parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise StopRun('BLOCKED', 'Diagnostic CLI directory is not private')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_mode & 0o077 or not info.st_mode & stat.S_IXUSR
                or not 0 < info.st_size <= 180 * 1024 * 1024):
            raise StopRun('BLOCKED', 'Diagnostic CLI file identity rejected')
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    def identity(value):
        return (value.st_dev,value.st_ino,value.st_mode,value.st_uid,value.st_nlink,
                value.st_size,value.st_mtime_ns,value.st_ctime_ns)
    if (digest != DIAGNOSTIC_SHA256 or identity(info) != identity(after)
            or identity(path.lstat()) != identity(after)):
        raise StopRun('BLOCKED', 'Diagnostic CLI changed or hash mismatch')
    socket = Path(DIAGNOSTIC_SOCKET)
    si = socket.lstat()
    if (socket.resolve(strict=True) != socket or not stat.S_ISSOCK(si.st_mode)
            or si.st_uid != os.getuid()):
        raise StopRun('BLOCKED', 'Original daemon socket required')
    # run_call refuses a missing/incompatible daemon; never serves or restarts it.
    return Calls._cli([str(path), '--socket', str(socket)], tool, args)


def execute(calls):
    launched = calls.invoke('launch_app', {'bundle_id': BUNDLE})
    if launched.get('bundle_id') != BUNDLE or type(launched.get('pid')) is not int:
        raise StopRun('BLOCKED', 'Launch result did not identify Calculator')
    calls.pid = launched['pid']
    # Launch may return before the first window exists. Only observations may be repeated.
    windows = []
    for _ in range(3):
        time.sleep(.3)
        result = calls.invoke('list_windows', {'pid': calls.pid})
        windows = [w for w in result.get('windows', [])
                   if w.get('pid') == calls.pid and w.get('title') == 'Calculator'
                   and w.get('app_name') == 'Calculator' and w.get('is_on_screen')]
        if windows:
            break
    if len(windows) != 1:
        raise StopRun('UNVERIFIED', 'No unique Calculator window')
    calls.window_id = windows[0]['window_id']
    for label in BUTTONS:
        state = calls.observe()
        button = button_in_window(state, label)
        try:
            calls.invoke('click', {'pid': calls.pid, 'window_id': calls.window_id,
                                  'session': calls.run_id, 'element_index': button['element_index'],
                                  'element_token': button['element_token']}, button=button)
        except StopRun as e:
            if e.status == 'UNVERIFIED' and calls.count < 30:
                # Preserve a fresh observation, but never resume an uncertain sequence.
                try:
                    calls.observe()
                except StopRun:
                    pass
            raise
    final = calls.observe()
    value = display_value(final)
    (calls.directory / 'final_state.json').write_text(json.dumps(final, ensure_ascii=False, indent=2))
    return {'status': 'UNVERIFIED', 'execution_complete': True, 'observed_display': value,
            'reason': 'M1 observation only; independent smoke assertion still required',
            'tool_calls': calls.count, 'final_screenshot': final['screenshot_file_path']}


def main():
    require_vm()
    root = Path.home() / 'AgentWorkspace'
    if root.is_symlink():
        raise StopRun('BLOCKED', 'Workspace must not be a symlink')
    root.mkdir(mode=0o700, exist_ok=True)
    directory = root / ('m1-' + uuid.uuid4().hex)
    directory.mkdir(mode=0o700)
    calls = Calls(directory)
    start = time.monotonic()
    try:
        report = execute(calls)
    except StopRun as e:
        report = {'status': e.status, 'execution_complete': False, 'reason': str(e),
                  'tool_calls': calls.count}
    finally:
        calls.log.close()
    report.update(run_id=directory.name, duration_ms=round((time.monotonic()-start)*1000))
    (directory / 'execution.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'directory': str(directory), **report}, indent=2))
    return directory, report


if __name__ == '__main__':
    main()
