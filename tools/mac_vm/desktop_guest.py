"""VM-only P6 control launcher. Never starts a model or grants its own lease."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sys
import threading
import time

from desktop_control import LeaseController
from desktop_control_http import control_server
from desktop_lease import LeaseGate
from desktop_runtime import DesktopGuestRuntime
from driver_smoke import require_vm

UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def private_write(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def prepare_guest(run_id, owner, epoch, *, approved):
    require_vm()  # Must precede all filesystem or listener side effects.
    if (approved is not True or not isinstance(run_id, str) or not re.fullmatch('p2-' + UUID, run_id)
            or not isinstance(owner, str) or not re.fullmatch(UUID, owner)
            or type(epoch) is not int or epoch < 1):
        raise ValueError('explicit approved execution binding required')
    root = Path.home() / 'C0Evidence'
    if root.resolve() != root:
        raise ValueError('canonical evidence root required')
    root.mkdir(mode=0o700, exist_ok=True)
    LeaseGate.private(root.stat(), directory=True)
    directory = root / run_id
    directory.mkdir(mode=0o700)  # Never resume/reuse a run or overwrite evidence.
    controller = LeaseController(directory / 'lease.json', run_id=run_id, owner=owner, epoch=epoch, clock=time.time)
    model_token, control_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    runtime = DesktopGuestRuntime(directory, controller, model_token=model_token, control_token=control_token,
                                   shared_lock=root / 'bridge.lock')
    server = None
    try:
        private_write(directory / 'bridge-token', model_token)
        private_write(directory / 'control-token', control_token)
        server = control_server(controller, control_token, runtime=runtime)
        server.timeout = .25
        ready = {'binding': runtime.status()['binding'], 'pid': os.getpid(),
                 'controlHost': '127.0.0.1', 'controlPort': server.server_port,
                 'modelUrl': 'http://192.168.64.3:8766', 'activated': False}
        private_write(directory / 'guest-ready.json', json.dumps(ready))
        return runtime, server
    except Exception:
        if server is not None:
            server.server_close()
        runtime.close()
        raise


def serve_guest(runtime, server, stopping, *, clock=time.monotonic):
    deadline = clock() + 3600
    try:
        while not stopping.is_set() and not runtime.closed and clock() < deadline:
            server.handle_request()
    finally:
        # Close admission before releasing the global guest desktop lock.
        try:
            runtime.close()
        finally:
            server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--epoch', type=int, required=True)
    parser.add_argument('--approve-task', action='store_true')
    args = parser.parse_args(argv)
    stopping = threading.Event()
    previous = {}
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, lambda *_: stopping.set())
        runtime, server = prepare_guest(args.run, args.owner, args.epoch, approved=args.approve_task)
        print('P6_GUEST_CONTROL_READY', flush=True)
        serve_guest(runtime, server, stopping)
        return 0
    except Exception:
        print('P6_GUEST_UNCONFIRMED_REQUIRES_REVIEW', file=sys.stderr, flush=True)
        return 1
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


if __name__ == '__main__':
    raise SystemExit(main())
