"""Lifecycle adapter only: never creates a model session or dispatches GUI work."""
import threading
from backend.control import write_control
from backend.desktop_client import ControlUnconfirmed


class DesktopExecutionControl:
    def __init__(self, service, client, *, task_id, owner, epoch):
        expected = dict(version=1, runId='p2-' + task_id, owner=owner, epoch=epoch)
        if client.identity != expected:
            raise ValueError('guest client must bind original task and execution owner')
        self.service, self.client = service, client
        self.task_id, self.owner, self.epoch = task_id, owner, epoch
        self.sequence = 0
        self.closed = False
        self.local_revoked = self.guest_revoked = False
        self.lock = threading.RLock()

    def refresh(self):
        with self.lock:
            if self.closed:
                raise ControlUnconfirmed('DESKTOP_CONTROL_CLOSED')
            try:
                if self.service.heartbeat(self.task_id, self.owner, self.epoch):
                    raise ControlUnconfirmed('DESKTOP_STOP_REQUESTED')
                self.sequence += 1
                return self.client.renew(self.sequence, lambda: self.service.desktop_authority(
                    self.task_id, self.owner, self.epoch, clock=self.client.clock))
            except Exception:
                # Even if acknowledgement is lost, never issue another renewal.
                self.close()
                raise ControlUnconfirmed('DESKTOP_CONTROL_REFRESH_UNCONFIRMED') from None

    def close(self):
        with self.lock:
            self.closed = True  # Remains true even if either revocation fails.
            try:
                write_control(self.service.settings.root / 'controls' / (self.task_id + '.json'),
                              run_id='p2-' + self.task_id, epoch=self.epoch, owner=self.owner,
                              expires_at=0, stopped=True)
                self.local_revoked = True
            except (OSError, ValueError, KeyError, TypeError):
                self.local_revoked = False
            try:
                self.guest_revoked = self.client.revoke()['stopped'] is True
            except Exception:
                self.guest_revoked = False
            return {'localRevoked': self.local_revoked, 'guestRevoked': self.guest_revoked,
                    'closed': True, 'inflightCancellationConfirmed': False}
