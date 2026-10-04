"""Owned SSH control tunnel; no VM launch, credential copy or lease grant."""
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import threading
import time

from backend.desktop_client import ControlUnconfirmed, DesktopControlClient


def check_tunnel_port(port):
    """Conservative preflight, not a reservation or proof of SSH ownership."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('loopback tunnel port required')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(('127.0.0.1', port))


class GuestControlTunnel:
    def __init__(self, *, root, ssh_wrapper, guest_port, client):
        self.root = Path(root).absolute()
        self.wrapper = Path(ssh_wrapper).absolute()
        for path, directory in ((self.root, True), (self.wrapper, False)):
            if path.resolve(strict=True) != path:
                raise ValueError('canonical trusted tunnel paths required')
            info = path.stat()
            if ((not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode))
                    or info.st_uid != os.getuid() or info.st_mode & 0o077):
                raise ValueError('private trusted tunnel paths required')
        if not os.access(self.wrapper, os.X_OK):
            raise ValueError('executable SSH wrapper required')
        if not isinstance(client, DesktopControlClient) or client.identity['runId'] != self.root.name:
            raise ValueError('fixed run control client required')
        if type(guest_port) is not int or not 1 <= guest_port <= 65535:
            raise ValueError('guest loopback port required')
        self.client, self.guest_port = client, guest_port
        self.process = None
        self.attempted = False
        self.lock = threading.RLock()

    def start(self):
        with self.lock:
            if self.attempted:
                raise ControlUnconfirmed('GUEST_TUNNEL_REQUIRES_RECONCILIATION')
            self.attempted = True
            # Never claim or terminate an existing listener. The bind check is
            # not ownership proof; SSH must bind itself and pass identity probe.
            check_tunnel_port(self.client.port)
            args = [str(self.wrapper), '-F', '/dev/null', '-N', '-T', '-o', 'ExitOnForwardFailure=yes',
                    '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no', '-o', 'ControlMaster=no',
                    '-o', 'ControlPath=none', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
                    '-L', f'127.0.0.1:{self.client.port}:127.0.0.1:{self.guest_port}']
            intent = self.root / 'desktop-tunnel-intent.json'
            fd = os.open(intent, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as file:
                json.dump({'binding': self.client.identity, 'hostPort': self.client.port,
                           'guestPort': self.guest_port}, file)
                file.flush()
                os.fsync(file.fileno())
            try:
                self.process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL, start_new_session=True)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if self.process.poll() is not None:
                        raise ControlUnconfirmed('GUEST_TUNNEL_EXITED')
                    try:
                        observed = self.client.inspect()
                    except ControlUnconfirmed as error:
                        if str(error) != 'GUEST_CONTROL_UNCONFIRMED':
                            raise  # Wrong identity is not a startup delay.
                        time.sleep(.05)
                        continue
                    if self.process.poll() is not None or time.monotonic() >= deadline:
                        raise ControlUnconfirmed('GUEST_TUNNEL_UNCONFIRMED')
                    return observed
                raise ControlUnconfirmed('GUEST_TUNNEL_START_TIMEOUT')
            except Exception:
                self.close()
                raise

    def close(self):
        """Close only our child. Caller must separately revoke guest authority."""
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                return
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    raise ControlUnconfirmed('GUEST_TUNNEL_TERMINATION_UNCONFIRMED') from None
