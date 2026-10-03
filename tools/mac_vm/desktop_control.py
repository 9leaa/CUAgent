"""Trusted guest lease storage; not exposed as a model tool or network service."""
from contextlib import contextmanager
import fcntl
import json
import math
import os
import tempfile
from desktop_lease import LeaseGate


class LeaseController:
    def __init__(self, path, *, run_id, owner, epoch, clock):
        self.gate = LeaseGate(path, run_id=run_id, owner=owner, epoch=epoch, clock=clock)
        self.path = self.gate.path

    @contextmanager
    def lock(self):
        parent = self.path.parent
        if parent.resolve(strict=True) != parent:
            raise ValueError('control parent symlink')
        LeaseGate.private(parent.stat(), directory=True)
        fd = os.open(parent / (self.path.name + '.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        with os.fdopen(fd, 'r+b') as file:
            LeaseGate.private(os.fstat(file.fileno()))
            fcntl.flock(file, fcntl.LOCK_EX)
            yield

    def existing(self):
        try:
            record = self.gate.read()
        except FileNotFoundError:
            if self.path.is_symlink():
                raise ValueError('lease symlink denied')
            return None
        expected = dict(version=1, runId=self.gate.run_id, owner=self.gate.owner, epoch=self.gate.epoch)
        if (not isinstance(record, dict) or any(record.get(k) != v for k, v in expected.items())
                or any(type(record.get(k)) is not int for k in ('version', 'epoch', 'sequence', 'issuedAt', 'expiresAt', 'ttlMs'))
                or type(record.get('stopped')) is not bool or record['sequence'] < 1
                or not 1 <= record['ttlMs'] <= 30000
                or type(record.get('notAfterMs')) is not int
                or record['expiresAt'] != min(record['issuedAt'] + record['ttlMs'], record['notAfterMs'])
                or record['expiresAt'] <= record['issuedAt']):
            raise ValueError('invalid or conflicting lease record')
        return record

    def replace(self, value):
        fd, temporary = tempfile.mkstemp(prefix='.lease-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as file:
                json.dump(value, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def renew(self, sequence, ttl_ms=20000, *, not_after_ms=None):
        if type(sequence) is not int or sequence < 1 or type(ttl_ms) is not int or not 1 <= ttl_ms <= 30000:
            raise ValueError('bounded integer sequence and TTL required')
        if not_after_ms is not None and type(not_after_ms) is not int:
            raise ValueError('integer guest deadline required')
        with self.lock():
            old = self.existing()
            now = self.gate.clock() * 1000
            if not math.isfinite(now):
                raise ValueError('invalid guest clock')
            now = int(now)
            if old:
                if old['stopped']:
                    raise ValueError('lease permanently stopped')
                if now < old['issuedAt'] or now >= old['expiresAt']:
                    self.replace({**old, 'stopped': True})
                    raise ValueError('lease expired or clock moved backwards; stopped')
                if sequence < old['sequence']:
                    raise ValueError('stale renewal sequence')
                if sequence == old['sequence']:
                    if ttl_ms != old['ttlMs'] or (not_after_ms is not None and not_after_ms != old['notAfterMs']):
                        raise ValueError('renewal identity conflict')
                    return old  # ACK retry never extends the original lease.
            deadline = now + ttl_ms if not_after_ms is None else not_after_ms
            if deadline <= now or deadline > now + 30000:
                raise ValueError('guest deadline unavailable or out of bounds')
            value = dict(version=1, runId=self.gate.run_id, owner=self.gate.owner, epoch=self.gate.epoch,
                         sequence=sequence, issuedAt=now, expiresAt=min(now + ttl_ms, deadline),
                         ttlMs=ttl_ms, notAfterMs=deadline, stopped=False)
            self.replace(value)
            return value

    def revoke(self):
        with self.lock():
            old = self.existing()
            if old is None:
                # Tombstone also prevents a delayed initial grant after stop.
                old = dict(version=1, runId=self.gate.run_id, owner=self.gate.owner, epoch=self.gate.epoch,
                           sequence=1, issuedAt=0, expiresAt=1, ttlMs=1, notAfterMs=1, stopped=True)
            value = {**old, 'stopped': True}
            self.replace(value)
            return value
