"""VM-only TextEdit identity/normal termination; no CLI or model registration."""
import json
import os
import subprocess

from desktop_app_cleanup import ApplicationIdentity
from driver_smoke import require_vm
from real_app_bridge import EXECUTABLE


# Only validated integers and a fixed executable are interpolated. Query and
# termination use the same NSRunningApplication object, never app-name lookup.
SCRIPT = r'''
ObjC.import('AppKit');
function run() {
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
}
'''


def _pid(pid):
    if type(pid) is not int or not 0 < pid <= 2**31 - 1:
        raise ValueError('invalid PID')


def _request(pid, started=None):
    _pid(pid)
    require_vm()  # Host refusal must happen before queries or normal quit.
    script = (SCRIPT.replace('__PID__', str(pid))
              .replace('__EXECUTABLE__', json.dumps(EXECUTABLE))
              .replace('__EXPECTED__', 'null' if started is None else str(started)))
    try:
        result = subprocess.run(['/usr/bin/osascript', '-l', 'JavaScript', '-e', script],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=3, check=False)
        if result.returncode != 0 or len(result.stdout) > 4096:
            raise ValueError('unconfirmed native response')
        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError('duplicate response field')
                obj[key] = value
            return obj
        return json.loads(result.stdout, object_pairs_hook=unique)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise RuntimeError('NATIVE_APP_RESPONSE_UNCONFIRMED') from None


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
