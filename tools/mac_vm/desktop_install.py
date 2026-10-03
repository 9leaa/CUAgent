"""Standalone pinned-source installer. Validates before creating a new directory."""
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

FILES = ('desktop_guest.py', 'desktop_export.py', 'desktop_runtime.py', 'desktop_control.py',
         'desktop_control_http.py', 'desktop_lease.py', 'desktop_tools_http.py', 'desktop_evidence.py',
         'real_app_bridge.py', 'real_app_verifier.py', 'c0_bridge.py', 'c0_cases.py', 'c0_identity.py',
         'driver_smoke.py', 'LICENSE-cua.md')


def install_package(raw, commit, home):
    if not isinstance(raw, bytes) or len(raw) > 1024 * 1024 or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('invalid deployment')
    package = json.loads(raw)
    if set(package) != {'commit', 'files'} or package['commit'] != commit or set(package['files']) != set(FILES):
        raise ValueError('deployment identity mismatch')
    contents, hashes = {}, {}
    for name in FILES:
        entry = package['files'][name]
        if set(entry) != {'base64', 'sha256'}:
            raise ValueError('invalid source entry')
        data = base64.b64decode(entry['base64'], validate=True)
        digest = hashlib.sha256(data).hexdigest()
        if not 0 < len(data) <= 256 * 1024 or digest != entry['sha256']:
            raise ValueError('source changed')
        if name.endswith('.py'):
            compile(data, name, 'exec')  # Parse only. Never import or execute it.
        contents[name], hashes[name] = data, digest
    home = Path(home).absolute()
    if home.resolve(strict=True) != home or home.stat().st_uid != os.getuid():
        raise ValueError('canonical owned home required')
    target = home / ('CUAgent-p6-' + commit)
    target.mkdir(mode=0o700)  # Partial previous installation requires review.
    manifest = json.dumps({'commit': commit, 'files': hashes}, sort_keys=True).encode()
    for name, data in [*contents.items(), ('deployment-manifest.json', manifest)]:
        fd = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    return {'deployment': str(target), 'manifestSha256': hashlib.sha256(manifest).hexdigest()}


def main():
    try:
        if sys.platform != 'darwin' or getpass.getuser() != 'mvpagent' or os.geteuid() == 0:
            raise ValueError('ordinary VM account required')
        model = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'], text=True, timeout=5).strip()
        if not model.startswith('VirtualMac') or Path.home() != Path('/Users/mvpagent') or len(sys.argv) != 2:
            raise ValueError('fixed VM required')
        result = install_package(sys.stdin.buffer.read(1024 * 1024 + 1), sys.argv[1], Path.home())
        print(json.dumps(result))
        return 0
    except Exception:
        print('P6_DEPLOYMENT_UNCONFIRMED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
