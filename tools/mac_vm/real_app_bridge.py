"""Opt-in, VM-only TextEdit trial. No fixed answer in the execution policy."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import plistlib
import subprocess
import time
from dataclasses import replace
from types import MappingProxyType
from c0_bridge import Task, main
from c0_cases import UICase
from driver_smoke import Calls, StopRun, require_vm

EXECUTABLE = '/System/Applications/TextEdit.app/Contents/MacOS/TextEdit'
REGISTRY = MappingProxyType({'real_textedit': UICase(
    'real_textedit', 'handoff.txt', '', (), (), 'com.apple.TextEdit', 'TextEdit', EXECUTABLE)})


def require_unlocked():
    require_vm()
    data = plistlib.loads(subprocess.check_output(['/usr/sbin/ioreg', '-n', 'Root', '-d1', '-a'], timeout=5))
    if not isinstance(data, dict) or data.get('IOConsoleLocked', False) is not False:
        raise StopRun('BLOCKED', 'Unavailable or locked VM console')
    users = data.get('IOConsoleUsers', [])
    active = [user for user in users if user.get('kCGSSessionUserNameKey') == 'mvpagent'
              and user.get('kCGSSessionOnConsoleKey') is True and user.get('kCGSessionLoginDoneKey') is True]
    if len(active) != 1 or active[0].get('CGSSessionScreenIsLocked', False) is not False:
        raise StopRun('BLOCKED', 'Test VM graphic session is locked or unavailable; no dispatch')


def textedit_identity(pid):
    if type(pid) is not int or pid <= 0:
        raise StopRun('BLOCKED', 'Invalid TextEdit PID')
    lib = ctypes.CDLL('/usr/lib/libproc.dylib')
    lib.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    lib.proc_pidpath.restype = ctypes.c_int
    buffer = ctypes.create_string_buffer(4096)
    if lib.proc_pidpath(pid, buffer, len(buffer)) <= 0 or os.fsdecode(buffer.value) != EXECUTABLE:
        raise StopRun('BLOCKED', 'PID no longer belongs to system TextEdit')


def body_from_state(state):
    # Read the native AX value, not menus, model output, or file contents.
    elements = state.get('elements', [])
    indexed = {element['element_index']: element for element in elements}
    bodies = []
    for element in elements:
        if element.get('role') != 'AXTextArea' or not isinstance(element.get('value'), str):
            continue
        ancestor = element
        seen = set()
        while ancestor and ancestor.get('element_index') not in seen:
            seen.add(ancestor.get('element_index'))
            if ancestor.get('role') == 'AXWindow':
                if ancestor.get('label') == state.get('window_title', 'handoff.txt'):
                    bodies.append(element['value'])
                break
            ancestor = indexed.get(ancestor.get('parent_index'))
    if bodies:
        if len(bodies) != 1:
            raise StopRun('UNVERIFIED', 'Ambiguous native TextEdit AX body')
        return bodies[0]
    tree = state.get('tree_markdown', '').split('\n- ', 1)[0]
    values = re.findall(r'AXTextArea(?: [^=\n]*)? = "((?:\\.|[^"\\])*)"', tree)
    if len(values) != 1:
        raise StopRun('UNVERIFIED', 'Need one native TextEdit AX body')
    try:
        return json.loads('"' + values[0] + '"')
    except json.JSONDecodeError:
        # This Driver emits literal newlines in AX values.
        return values[0]


class RealAppTask(Task):
    RAW_TOOLS = (Task.RAW_TOOLS - {'press_key'}) | {'bring_to_front', 'hotkey'}
    SIDE_EFFECT_TOOLS = Task.SIDE_EFFECT_TOOLS | {'bring_to_front', 'hotkey'}
    def __init__(self, directory, transport=Calls.cli, identity=None, *, approved=False, case_id='real_textedit', environment=None):
        self.environment = environment or require_unlocked
        self.environment()
        super().__init__(directory, transport, identity or textedit_identity,
                         approved=approved, case_id=case_id, registry=REGISTRY)
        self.case = replace(self.case, title='handoff-' + self.run_id + '.txt')
        artifacts = directory / 'artifacts'
        if artifacts.is_symlink():
            raise StopRun('BLOCKED', 'Artifact root symlink denied')
        artifacts.mkdir(mode=0o700, exist_ok=True)
        self.document = artifacts / self.case.title
        if not self.used and not self.stopped.is_set():
            with self.document.open('xb'):
                pass
            self.record({'event': 'setup_empty_document', 'bytes': 0,
                         'sha256': hashlib.sha256(b'').hexdigest()})
        if self.document.is_symlink() or not self.document.is_file():
            raise StopRun('BLOCKED', 'Need regular task document')
        self.launch_args = {'bundle_id': self.case.bundle, 'creates_new_application_instance': True,
                            'urls': [str(self.document)]}
        self.focus_attempted = False
        self.activation_pending = False
        self.frame_retry_used = False

    def validate_raw(self, tool, args):
        self.environment()
        if tool == 'bring_to_front':
            if (args != {'pid': self.pid, 'window_id': self.window} or self.pid is None
                    or not self.activation_pending):
                raise StopRun('BLOCKED', 'Only bound task window activation allowed')
            self.identity(self.pid)
        elif tool == 'hotkey':
            if args != {'pid': self.pid, 'window_id': self.window, 'session': self.run_id,
                        'keys': ['cmd', 's'], 'delivery_mode': 'foreground'} or self.pid is None:
                raise StopRun('BLOCKED', 'Only task-window Command-S allowed')
            self.identity(self.pid)
        else:
            super().validate_raw(tool, args)

    def observe(self):
        try:
            return super().observe()
        except StopRun:
            rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
            states = [row['value'] for row in rows if row['event'] == 'result' and row.get('tool') == 'get_window_state']
            state = states[-1] if states else {}
            retry_frame = (not self.frame_retry_used and not self.uncertain and not self.stopped.is_set()
                           and self.used < 30 and state.get('pid') == self.pid and state.get('window_id') == self.window
                           and state.get('app_name') == self.case.app_name and state.get('window_title') == self.case.title
                           and state.get('screenshot_error', {}).get('code') == 'px_frame_mismatch')
            if retry_frame:
                self.frame_retry_used = True
                self.record({'event': 'frame_reobserve', 'source_used': self.used, 'reason': 'px_frame_mismatch'})
                try:
                    return super().observe()
                except Exception:
                    self.stop()
                    raise
            recoverable = (not self.focus_attempted and not self.uncertain and not self.stopped.is_set()
                           and self.used <= 27 and state.get('pid') == self.pid
                           and state.get('window_id') == self.window
                           and state.get('window_title') == self.case.title
                           and state.get('app_name') == self.case.app_name
                           and state.get('screenshot_frame_valid') is True
                           and state.get('degraded_reason', '').startswith('ax_window_unresolved:'))
            if not recoverable:
                self.stop()
                raise
            self.focus_attempted = True
            self.record({'event': 'observation_recovery', 'reason': 'bound TextEdit AX unresolved',
                         'pid': self.pid, 'window_id': self.window, 'source_used': self.used})
            self.activation_pending = True
            try:
                self.raw('bring_to_front', {'pid': self.pid, 'window_id': self.window})
            except Exception:
                self.stop()
                raise
            finally:
                self.activation_pending = False
            try:
                return super().observe()
            except Exception:
                self.stop()
                raise

    def type_text(self, args):
        if set(args) != {'snapshot_id', 'element_index', 'element_token', 'text'}:
            raise StopRun('BLOCKED', 'Unexpected input fields')
        text = args['text']
        if (type(args['element_index']) is not int or not isinstance(args['snapshot_id'], str)
                or not isinstance(args['element_token'], str)):
            raise StopRun('BLOCKED', 'Invalid AX identity types')
        if not isinstance(text, str) or not text or '\0' in text or len(text.encode('utf8')) > 4096:
            raise StopRun('BLOCKED', 'Text must be nonempty UTF-8 <=4 KiB without NUL')
        element = self.ui_element(args, ('AXTextArea',))
        self.snapshot = None
        result = self.raw('type_text', {'pid': self.pid, 'window_id': self.window, 'session': self.run_id,
                                      'element_index': args['element_index'], 'element_token': args['element_token'],
                                      'text': text})
        self.record({'event': 'attempted_input', 'snapshot_id': args['snapshot_id'],
                     'element_index': element['element_index'], 'bytes': len(text.encode('utf8')),
                     'sha256': hashlib.sha256(text.encode('utf8')).hexdigest()})
        return result

    def click(self, args):
        raise StopRun('BLOCKED', 'Arbitrary clicking is not approved for TextEdit')

    def save(self, args):
        if set(args) != {'snapshot_id'}:
            raise StopRun('BLOCKED', 'Unexpected Save fields')
        state = self.snapshot
        if not state or args['snapshot_id'] != state['snapshot_id'] or time.monotonic() - self.observed_at > 30:
            raise StopRun('BLOCKED', 'Fresh observation required before Save')
        body_from_state(state)
        self.snapshot = None
        result = self.raw('hotkey', {'pid': self.pid, 'window_id': self.window, 'session': self.run_id,
                                   'keys': ['cmd', 's'], 'delivery_mode': 'foreground'})
        self.record({'event': 'attempted_save', 'snapshot_id': args['snapshot_id']})
        return result

    def observed_value(self):
        value = body_from_state(self.snapshot)
        if self.document.is_symlink() or self.document.stat().st_size > 4096:
            raise StopRun('BLOCKED', 'Document link or size invalid')
        saved = self.document.read_bytes()
        if saved not in (value.encode('utf8'), (value + '\n').encode('utf8')):
            raise StopRun('UNVERIFIED', 'Current native body not saved to authorized task file')
        return saved.decode('utf8')

    def verify(self):
        self.observe()
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        expected_path = self.directory / 'verifier-expected.txt'
        if expected_path.is_symlink():
            raise StopRun('BLOCKED', 'Oracle symlink denied')
        expected = expected_path.read_bytes()
        body = self.observed_value().encode('utf8')
        result_path = self.task_file('result.txt')
        result = result_path.read_bytes()
        dispatched = [row for row in rows if row['event'] == 'dispatch']
        returned = [row for row in rows if row['event'] == 'result']
        inputs = [row for row in rows if row['event'] == 'attempted_input']
        saves = [row for row in rows if row['event'] == 'attempted_save']
        readbacks = [row for row in returned if row.get('tool') == 'read_result']
        from real_app_verifier import verify_evidence
        acceptance = verify_evidence(rows, expected, self.document.read_bytes(), result, self.snapshot)
        passed = acceptance['status'] == 'SUCCEEDED' and not self.stopped.is_set() and not self.uncertain
        report = {'status': 'SUCCEEDED' if passed else 'UNVERIFIED', 'case_id': self.case_id,
                  'raw_calls': self.used, 'document_sha256': hashlib.sha256(body).hexdigest(),
                  'document_bytes': len(body), 'inputs': len(inputs), 'saves': len(saves),
                  'file_readback': result.decode('utf8'), 'fresh_display': body_from_state(self.snapshot),
                  'saved_body': body.decode('utf8'),
                  'expected': expected.decode('utf8')}
        with self.task_file('verification.json').open('x') as output:
            json.dump(report, output, indent=2)
        return report


if __name__ == '__main__':
    main(RealAppTask, REGISTRY, stage='REAL_APP')
