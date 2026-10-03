"""Trusted SSH export collection; never issues GUI actions or marks success."""
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import stat
import subprocess
import time

from backend.desktop_bundle import decode_guest_bundle
from backend.desktop_client import DesktopControlClient
from backend.desktop_contract import DesktopSubmission

GUEST_PYTHON = '/Users/mvpagent/.local/cuagent-python-3.12.14-20260929/python/bin/python3.12'


def run_bounded(args, payload, *, limit=65 * 1024 * 1024, timeout=45, input_limit=32768):
    """Bound both pipe directions and elapsed time; never invoke a local shell."""
    if (type(input_limit) is not int or not 1 <= input_limit <= 1024 * 1024
            or not isinstance(payload, bytes) or len(payload) > input_limit or limit < 1 or timeout <= 0):
        raise ValueError('invalid collection bounds')
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    output = bytearray()
    offset = 0
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            os.set_blocking(process.stdout.fileno(), False)
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ)
            if payload:
                selector.register(process.stdin, selectors.EVENT_WRITE)
            else:
                process.stdin.close()
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('collection timeout')
                for key, _ in selector.select(min(remaining, .1)):
                    if key.fileobj is process.stdin:
                        offset += os.write(process.stdin.fileno(), payload[offset:offset + 4096])
                        if offset == len(payload):
                            selector.unregister(process.stdin)
                            process.stdin.close()
                    else:
                        chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(output)))
                        if not chunk:
                            selector.unregister(process.stdout)
                        output.extend(chunk)
                        if len(output) > limit:
                            raise ValueError('collection output limit')
            remaining = deadline - time.monotonic()
            if remaining <= 0 or process.wait(timeout=remaining) != 0:
                raise ValueError('collection exit unconfirmed')
        return bytes(output)
    except Exception:
        raise RuntimeError('GUEST_COLLECTION_UNCONFIRMED') from None
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        process.stdout.close()
        process.stdin.close()


def private_path(path, *, directory):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path:
        raise ValueError('canonical collection path required')
    info = path.stat()
    if ((not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode))
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ValueError('private collection path required')
    return path


def save_exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def collect_guest_bundle(*, root, ssh_wrapper, deployment, client, submission):
    root = private_path(root, directory=True)
    wrapper = private_path(ssh_wrapper, directory=False)
    if (not os.access(wrapper, os.X_OK) or not isinstance(client, DesktopControlClient)
            or root.name != client.identity['runId'] or not isinstance(submission, DesktopSubmission)
            or not isinstance(deployment, str)
            or not re.fullmatch(r'/Users/mvpagent/CUAgent-p6-[0-9a-f]{40}', deployment)):
        raise ValueError('trusted collection binding required')
    before = client.status()
    lease = client.inspect().get('lease')
    if not before['stopped'] or before['pendingCalls'] or before['rawCalls'] < 1 or not lease or not lease['stopped']:
        raise ValueError('revoked idle guest required')
    identity = client.identity.copy()
    uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if not re.fullmatch('p2-' + uuid, identity['runId']) or not re.fullmatch(uuid, identity['owner']):
        raise ValueError('fixed UUID identities required')
    save_exclusive(root / 'desktop-collection-intent.json', json.dumps(identity).encode())
    command = shlex.join([GUEST_PYTHON, deployment + '/desktop_export.py', '--run', identity['runId'],
                          '--owner', identity['owner'], '--epoch', str(identity['epoch'])])
    args = [str(wrapper), '-F', '/dev/null', '-T', '-o', 'ClearAllForwardings=yes',
            '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no', '-o', 'ControlMaster=no', '-o', 'ControlPath=none', command]
    raw = run_bounded(args, json.dumps({'lines': list(submission.lines)}, ensure_ascii=False).encode())
    save_exclusive(root / 'guest-evidence.tar', raw)
    after = client.status()
    if (not after['stopped'] or after['pendingCalls'] or after['rawCalls'] != before['rawCalls']
            or client.inspect().get('lease') != lease):
        raise RuntimeError('GUEST_COLLECTION_STATE_CHANGED')
    return decode_guest_bundle(raw, submission=submission, run_id=identity['runId'],
                               owner=identity['owner'], epoch=identity['epoch'])
