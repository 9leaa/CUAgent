"""Standalone VM bootstrap, sent by trusted SSH; secrets only in private receipt."""
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def private_read(path, limit):
    if path.resolve(strict=True) != path:
        raise ValueError('linked bootstrap source')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > limit:
            raise ValueError('private bootstrap source required')
        raw = stream.read(limit + 1)
    if len(raw) != info.st_size:
        raise ValueError('bootstrap source changed')
    return raw


def bootstrap(home, *, commit, manifest_sha, run_id, owner, epoch):
    if (not re.fullmatch(r'[0-9a-f]{40}', commit) or not re.fullmatch(r'[0-9a-f]{64}', manifest_sha)
            or not re.fullmatch('p2-' + UUID, run_id) or not re.fullmatch(UUID, owner)
            or type(epoch) is not int or epoch < 1):
        raise ValueError('fixed bootstrap binding required')
    home = Path(home).absolute()
    deployment = home / ('CUAgent-p6-' + commit)
    if deployment.resolve(strict=True) != deployment or deployment.stat().st_mode & 0o077:
        raise ValueError('private deployment required')
    raw = private_read(deployment / 'deployment-manifest.json', 65536)
    if hashlib.sha256(raw).hexdigest() != manifest_sha:
        raise ValueError('deployment manifest changed')
    manifest = json.loads(raw)
    if manifest.get('commit') != commit or not isinstance(manifest.get('files'), dict) or 'desktop_guest.py' not in manifest['files']:
        raise ValueError('deployment identity mismatch')
    for name, digest in manifest['files'].items():
        if not re.fullmatch(r'[a-zA-Z0-9_-]+\.(?:py|md)', name):
            raise ValueError('invalid source path')
        if hashlib.sha256(private_read(deployment / name, 256 * 1024)).hexdigest() != digest:
            raise ValueError('deployment source changed')
    run = home / 'C0Evidence' / run_id
    if os.path.lexists(run) or os.path.lexists(home / 'C0Evidence/bridge.lock.quarantine'):
        raise ValueError('existing run or quarantined desktop requires review')
    logs = home / 'P6Launch'
    if logs.resolve() != logs:
        raise ValueError('linked log directory')
    logs.mkdir(mode=0o700, exist_ok=True)
    if logs.stat().st_uid != os.getuid() or logs.stat().st_mode & 0o077:
        raise ValueError('private logs required')
    fd = os.open(logs / (run_id + '.log'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as log:
        process = subprocess.Popen([sys.executable, str(deployment / 'desktop_guest.py'), '--run', run_id,
                                    '--owner', owner, '--epoch', str(epoch), '--approve-task'],
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ValueError('guest exited before ready')
        try:
            ready = json.loads(private_read(run / 'guest-ready.json', 4096))
            model_token = private_read(run / 'bridge-token', 128).decode()
            control_token = private_read(run / 'control-token', 128).decode()
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(.1)
            continue
        if (ready.get('binding') != {'version': 1, 'runId': run_id, 'owner': owner, 'epoch': epoch}
                or type(ready.get('pid')) is not int or ready['pid'] != process.pid
                or ready.get('activated') is not False or ready.get('controlHost') != '127.0.0.1'
                or type(ready.get('controlPort')) is not int or not 1 <= ready['controlPort'] <= 65535
                or ready.get('modelUrl') != 'http://192.168.64.3:8766'
                or model_token == control_token
                or any(not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', token) for token in (model_token, control_token))
                or process.poll() is not None):
            raise ValueError('guest ready identity mismatch')
        return {**ready, 'modelToken': model_token, 'controlToken': control_token}
    raise ValueError('guest readiness unconfirmed; do not restart')


def main():
    try:
        if (sys.platform != 'darwin' or getpass.getuser() != 'mvpagent' or os.geteuid() == 0
                or Path.home() != Path('/Users/mvpagent') or len(sys.argv) != 6):
            raise ValueError('ordinary VM required')
        if not subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'], text=True, timeout=5).strip().startswith('VirtualMac'):
            raise ValueError('VM required')
        result = bootstrap(Path.home(), commit=sys.argv[1], manifest_sha=sys.argv[2], run_id=sys.argv[3],
                           owner=sys.argv[4], epoch=int(sys.argv[5]))
        print(json.dumps(result))  # Trusted SSH caller saves privately; never log this receipt.
        return 0
    except Exception:
        print('P6_GUEST_BOOTSTRAP_UNCONFIRMED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
