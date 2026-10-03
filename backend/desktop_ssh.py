"""Generate a private P6 transport without copying credentials or discarding stdin."""
import os
import shlex
import stat
from pathlib import Path

from backend.desktop_collect import private_path, save_exclusive

SSH_BINARY = '/usr/bin/ssh'


def create_ssh_wrapper(*, root, known_hosts, askpass):
    root = private_path(root, directory=True)
    known_hosts = Path(known_hosts).absolute()
    info = known_hosts.stat()
    if (known_hosts.resolve(strict=True) != known_hosts or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022):
        raise ValueError('owned non-writable public host-key file required')
    askpass = private_path(askpass, directory=False)
    if not os.access(askpass, os.X_OK):
        raise ValueError('executable trusted askpass required')
    # These are operator-controlled paths, never task/model parameters. OpenSSH
    # parses the option value separately, so quote the known-hosts path there too.
    if any(char in str(path) for path in (known_hosts, askpass) for char in '\n\r\x00'):
        raise ValueError('single-line credential paths required')
    args = [SSH_BINARY, '-T', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile="' + str(known_hosts).replace('\\', '\\\\').replace('"', '\\"') + '"',
            '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'UpdateHostKeys=no',
            '-o', 'ConnectTimeout=5', '-o', 'NumberOfPasswordPrompts=1',
            'mvpagent@192.168.64.3']
    script = ('#!/bin/sh\nset -eu\nexport SSH_ASKPASS=' + shlex.quote(str(askpass))
              + '\nexport SSH_ASKPASS_REQUIRE=force\nexport DISPLAY=cuagent-p6\nexec '
              + shlex.join(args) + ' "$@"\n')
    target = root / 'desktop-vm-ssh'
    save_exclusive(target, script.encode())
    target.chmod(0o700)
    return target
