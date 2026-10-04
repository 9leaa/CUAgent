"""Read-only proof for settling this invocation's cleaned preparation failure."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

from backend.desktop_collect import private_path
from backend.desktop_bootstrap import validate_ready


@dataclass(frozen=True)
class PreparationClosed:
    run: Path
    owner: str
    epoch: int
    profile_sha256: str


def read_private(path):
    path = private_path(path, directory=False)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > 1024 * 1024):
            raise ValueError('private bounded preparation evidence required')
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) != info.st_size:
        raise ValueError('preparation evidence changed')
    return raw


def confirm_preparation_closed(*, root, home, task):
    root = private_path(root, directory=True)
    home = private_path(home, directory=True)
    if root.name != 'p2-' + task.id:
        raise ValueError('original preparation required')
    # Includes incomplete and symlinked intent files, not just valid receipts.
    forbidden = {'desktop-start-intent.json', 'desktop-session-start-intent.json',
                 'desktop-session-binding.json', 'create-request.json', 'session-created.json',
                 'model-select-request.json', 'prompt-request.json', 'prompt-response.json'}
    if any(path.name in forbidden or path.name.startswith(('app-', 'profile-apply-', 'profile-restore-'))
           for path in root.iterdir()):
        raise ValueError('execution or profile change requires review')
    identity = {'version': 1, 'runId': root.name, 'owner': task.owner, 'epoch': task.epoch}
    cleanup = {'binding': identity, 'closed': True, 'stopped': True,
               'active': False, 'rawCalls': 0, 'pendingCalls': 0}
    validate_ready(json.loads(read_private(root / 'guest-private-receipt.json')), identity)
    launch = json.loads(read_private(root / 'desktop-guest-start-intent.json'))
    if json.dumps(launch.get('binding'), sort_keys=True) != json.dumps(identity, sort_keys=True):
        raise ValueError('original launch binding required')
    for name, expected in [('desktop-prepare-cleanup-intent.json', identity),
                           ('desktop-prepare-cleanup.json', cleanup)]:
        observed = json.loads(read_private(root / name))
        if json.dumps(observed, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise ValueError('preparation cleanup binding mismatch')
    failure = json.loads(read_private(root / 'desktop-prepare-failure.json'))
    if (failure.get('taskId') != task.id or failure.get('runId') != root.name
            or failure.get('cleanupConfirmed') is not True
            or failure.get('guestStartAttempted') is not True or failure.get('guestReceiptPresent') is not True
            or failure.get('stage') not in ('control-client', 'tunnel-start', 'connection-record')):
        raise ValueError('confirmed preparation failure required')
    target = home / 'profiles/desktop/cordis.patch.yml'
    plan = json.loads(read_private(root / 'profile-plan.json'))
    before = read_private(root / 'profile-before.yml')
    digest = hashlib.sha256(before).hexdigest()
    if (type(plan.get('version')) is not int or plan['version'] != 1
            or plan.get('root') != str(root) or plan.get('home') != str(home)
            or plan.get('target') != str(target) or plan.get('beforeSha256') != digest
            or read_private(target) != before):
        raise ValueError('original profile unchanged proof required')
    return PreparationClosed(root, task.owner, task.epoch, digest)
