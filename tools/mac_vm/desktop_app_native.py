"""VM-only TextEdit identity/normal termination; no CLI or model registration."""
import json
import os
import subprocess
import re
import stat
from pathlib import Path

from desktop_app_cleanup import ApplicationIdentity
from driver_smoke import require_vm
from real_app_bridge import EXECUTABLE


class NativeRequestError(RuntimeError):
    """Fixed diagnostic vocabulary only; never serialize external exceptions."""
    def __init__(self, phase, code=None):
        if phase not in {'identity', 'build', 'send', 'reply', 'spawn', 'timeout', 'exit', 'protocol'}:
            raise ValueError('invalid native diagnostic phase')
        if code is not None and (type(code) is not int or not -(2**31) <= code < 2**31):
            raise ValueError('invalid native diagnostic code')
        super().__init__('NATIVE_APP_RESPONSE_UNCONFIRMED')
        self.diagnostic = {'phase': phase, 'code': code}


# Only validated integers and a fixed executable are interpolated. Query and
# termination use the same NSRunningApplication object, never app-name lookup.
SCRIPT = r'''
ObjC.import('AppKit');
function run() {
  let phase = 'identity';
  try {
  const pid = __PID__;
  const app = $.NSRunningApplication.runningApplicationWithProcessIdentifier(pid);
  if (!app || app.isNil()) return JSON.stringify({absent: true});
  const bundle = ObjC.unwrap(app.bundleIdentifier);
  const executable = ObjC.unwrap(app.executableURL.path);
  const date = app.launchDate;
  if (!date || date.isNil()) throw Error('IDENTITY_UNAVAILABLE');
  const started = Math.round(Number(date.timeIntervalSince1970) * 1000000);
  if (bundle !== 'com.apple.TextEdit' || executable !== __EXECUTABLE__ ||
      !Number.isSafeInteger(started) || started <= 0) throw Error('IDENTITY_CHANGED');
  const identity = {pid: pid, startedUs: started, executable: executable};
  const expected = __EXPECTED__;
  if (expected === null) return JSON.stringify(identity);
  if (started !== expected) throw Error('IDENTITY_CHANGED');
  return JSON.stringify({accepted: Boolean(app.terminate)});
  } catch (_) {
    return JSON.stringify({nativeFailure: {phase: phase, code: null}});
  }
}
'''


def _pid(pid):
    if type(pid) is not int or not 0 < pid <= 2**31 - 1:
        raise ValueError('invalid PID')


def _request(pid, started=None, document=None):
    _pid(pid)
    require_vm()  # Host refusal must happen before queries or normal quit.
    script = (SCRIPT.replace('__PID__', str(pid))
              .replace('__EXECUTABLE__', json.dumps(EXECUTABLE))
              .replace('__EXPECTED__', 'null' if started is None else str(started)))
    if document is not None:
        script = script.replace('return JSON.stringify({accepted: Boolean(app.terminate)});', r'''
  phase = 'build';
  const target = $.NSAppleEventDescriptor.descriptorWithProcessIdentifier(pid);
  const event = $.NSAppleEventDescriptor.appleEventWithEventClassEventIDTargetDescriptorReturnIDTransactionID(
    0x61657674, 0x6f646f63, target, -1, 0);
  const documents = $.NSAppleEventDescriptor.listDescriptor;
  documents.insertDescriptorAtIndex($.NSAppleEventDescriptor.descriptorWithFileURL(
    $.NSURL.fileURLWithPath(__DOCUMENT__)), 1);
  event.setParamDescriptorForKeyword(documents, 0x2d2d2d2d);
  const error = Ref();
  phase = 'send';
  const reply = event.sendEventWithOptionsTimeoutError(
    $.NSAppleEventSendWaitForReply | $.NSAppleEventSendNeverInteract, 1, error);
  if (!reply || reply.isNil()) {
    const value = error[0];
    const number = value && !value.isNil() ? Number(value.code) : null;
    const safe = Number.isInteger(number) && number >= -2147483648 && number <= 2147483647;
    return JSON.stringify({nativeFailure: {phase: phase, code: safe ? number : null}});
  }
  phase = 'reply';
  const code = reply.paramDescriptorForKeyword(0x6572726e);
  if (code && !code.isNil() && Number(code.int32Value) !== 0)
    return JSON.stringify({nativeFailure: {phase: phase, code: Number(code.int32Value)}});
  return JSON.stringify({accepted: true});
'''.replace('__DOCUMENT__', json.dumps(document)))
    try:
        result = subprocess.run(['/usr/bin/osascript', '-l', 'JavaScript', '-e', script],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=3, check=False)
        if result.returncode != 0:
            raise NativeRequestError('exit')
        if len(result.stdout) > 4096:
            raise ValueError('unconfirmed native response')
        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError('duplicate response field')
                obj[key] = value
            return obj
        value = json.loads(result.stdout, object_pairs_hook=unique)
        if type(value) is dict and 'nativeFailure' in value:
            failure = value['nativeFailure']
            if (set(value) != {'nativeFailure'} or type(failure) is not dict
                    or set(failure) != {'phase', 'code'}
                    or failure['phase'] not in ('identity', 'build', 'send', 'reply')):
                raise ValueError('invalid native failure envelope')
            raise NativeRequestError(failure['phase'], failure['code'])
        return value
    except subprocess.TimeoutExpired:
        raise NativeRequestError('timeout') from None
    except OSError:
        raise NativeRequestError('spawn') from None
    except (ValueError, subprocess.SubprocessError):
        raise NativeRequestError('protocol') from None


def read_identity(pid):
    value = _request(pid)
    if type(value) is dict and set(value) == {'absent'} and value['absent'] is True:
        # A missing AppKit entry alone could be an existing non-GUI process.
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except OSError:
            raise RuntimeError('NATIVE_PROCESS_PRESENCE_UNKNOWN') from None
        raise RuntimeError('NATIVE_APP_IDENTITY_UNAVAILABLE')
    if type(value) is not dict or set(value) != {'pid', 'startedUs', 'executable'}:
        raise RuntimeError('NATIVE_APP_IDENTITY_UNAVAILABLE')
    identity = ApplicationIdentity(value['pid'], value['startedUs'], value['executable'])
    if identity.pid != pid:
        raise RuntimeError('NATIVE_APP_IDENTITY_CHANGED')
    return identity


def request_terminate(identity):
    if type(identity) is not ApplicationIdentity or identity.started_us > 2**53 - 1:
        raise ValueError('captured native identity required')
    value = _request(identity.pid, identity.started_us)
    if type(value) is not dict or set(value) != {'accepted'} or type(value['accepted']) is not bool:
        raise RuntimeError('NATIVE_APP_TERMINATION_UNCONFIRMED')
    return value['accepted']  # Receipt/absence verification belongs to coordinator.


def request_open_document(identity, document):
    if type(identity) is not ApplicationIdentity or identity.started_us > 2**53 - 1:
        raise ValueError('captured native identity required')
    require_vm()
    path = Path(document).absolute()
    uuid = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
    pattern = r'/Users/mvpagent/C0Evidence/(p2-' + uuid + r')/artifacts/handoff-\1\.txt'
    if not re.fullmatch(pattern, str(path)) or path.resolve(strict=True) != path:
        raise ValueError('fixed original task document required')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or not 0 < info.st_size <= 4096:
        raise ValueError('saved owned document required')
    value = _request(identity.pid, identity.started_us, str(path))
    if type(value) is not dict or set(value) != {'accepted'} or value['accepted'] is not True:
        raise RuntimeError('NATIVE_DOCUMENT_OPEN_UNCONFIRMED')
    return True  # New window/AX/file proof remains the caller's responsibility.
