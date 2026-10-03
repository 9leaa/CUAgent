"""Bounded guest control client. No model calls; no automatic retry of mutations."""
import http.client
import json
import math
import re
import time
import threading


class ControlUnconfirmed(RuntimeError):
    pass


class DesktopControlClient:
    def __init__(self, *, port, token, run_id, owner, epoch, clock=time.monotonic):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('loopback tunnel port required')
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', token):
            raise ValueError('independent control token required')
        if not isinstance(run_id, str) or not run_id or not isinstance(owner, str) or not owner or type(epoch) is not int or epoch < 1:
            raise ValueError('fixed execution identity required')
        self.port, self.token, self.clock = port, token, clock
        self.identity = dict(version=1, runId=run_id, owner=owner, epoch=epoch)
        self._activation_attempted = False
        self._lifecycle_lock = threading.RLock()
        self._raw_calls = 0

    def validate_status(self, value):
        binding = value.get('binding')
        if (not isinstance(binding, dict) or binding != self.identity
                or type(binding.get('version')) is not int or type(binding.get('epoch')) is not int
                or any(type(value.get(key)) is not bool for key in ('active', 'stopped'))
                or any(type(value.get(key)) is not int for key in ('rawCalls', 'pendingCalls'))
                or not self._raw_calls <= value['rawCalls'] <= 30
                or not 0 <= value['pendingCalls'] <= value['rawCalls']):
            raise ControlUnconfirmed('GUEST_RUNTIME_STATUS_MISMATCH')
        port = value.get('modelPort')
        if ((port is not None and (type(port) is not int or not 1 <= port <= 65535))
                or (value['active'] and port is None)):
            raise ControlUnconfirmed('GUEST_RUNTIME_PORT_MISMATCH')
        self._raw_calls = value['rawCalls']
        return value

    def status(self):
        with self._lifecycle_lock:
            return self.validate_status(self.request('GET', '/status'))

    def activate(self, authority):
        """Single attempt; caller must close/quarantine on any unknown outcome."""
        with self._lifecycle_lock:
            if self._activation_attempted:
                raise ControlUnconfirmed('GUEST_ACTIVATION_REQUIRES_RECONCILIATION')
            self._activation_attempted = True
            start = self.clock()
            state = self.status()
            if state['active'] or state['stopped'] or state['rawCalls'] or state['pendingCalls']:
                raise ControlUnconfirmed('GUEST_RUNTIME_NOT_FRESH')
            observed = self.inspect()
            lease = self.validate(observed.get('lease'))
            guest_now = observed.get('clockMs')
            if type(guest_now) is not int or lease['stopped'] or guest_now < 0 or guest_now >= lease['expiresAt']:
                raise ControlUnconfirmed('GUEST_ACTIVATION_LEASE_UNAVAILABLE')
            deadline = authority()
            now = self.clock()
            if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                    or not math.isfinite(now) or not math.isfinite(start) or now < start or now >= deadline
                    or guest_now + math.ceil((now - start) * 1000) >= lease['expiresAt']):
                raise ControlUnconfirmed('GUEST_ACTIVATION_AUTHORITY_UNAVAILABLE')
            result = self.validate_status(self.request('POST', '/activate', {}))
            after = self.clock()
            if (not math.isfinite(after) or after < now or after >= deadline
                    or guest_now + math.ceil((after - start) * 1000) >= lease['expiresAt']
                    or not result['active'] or result['stopped'] or result['rawCalls'] or result['pendingCalls']):
                raise ControlUnconfirmed('GUEST_ACTIVATION_UNCONFIRMED')
            return result

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        try:
            connection.request(method, path, None if body is None else json.dumps(body),
                               {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
            response = connection.getresponse()
            raw = response.read(4097)
            if response.status != 200 or len(raw) > 4096:
                raise ValueError('response not confirmed')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError('response object required')
            return result
        except (OSError, http.client.HTTPException, ValueError, TypeError):
            raise ControlUnconfirmed('GUEST_CONTROL_UNCONFIRMED') from None
        finally:
            connection.close()

    def validate(self, record):
        if (not isinstance(record, dict) or any(record.get(k) != v for k, v in self.identity.items())
                or type(record.get('version')) is not int or type(record.get('epoch')) is not int
                or type(record.get('stopped')) is not bool
                or any(type(record.get(k)) is not int for k in ('sequence', 'issuedAt', 'expiresAt', 'ttlMs', 'notAfterMs'))
                or record['sequence'] < 1 or not 1 <= record['ttlMs'] <= 30000
                or record['expiresAt'] != min(record['issuedAt'] + record['ttlMs'], record['notAfterMs'])
                or record['expiresAt'] <= record['issuedAt']):
            raise ControlUnconfirmed('GUEST_CONTROL_IDENTITY_OR_DEADLINE_MISMATCH')
        return record

    def inspect(self):
        observed = self.request('GET', '/lease')
        binding = observed.get('binding')
        if (not isinstance(binding, dict) or binding != self.identity
                or type(binding.get('version')) is not int or type(binding.get('epoch')) is not int):
            raise ControlUnconfirmed('GUEST_CONTROL_BINDING_MISMATCH')
        if observed.get('lease') is not None:
            self.validate(observed['lease'])
        return observed

    def renew(self, sequence, authority):
        """authority must freshly return this fixed owner's monotonic deadline.

        The callback belongs to the trusted Worker, never the submitted task.
        Database lease/epoch checking is integrated separately.
        """
        if type(sequence) is not int or sequence < 1:
            raise ValueError('positive renewal sequence required')
        start = self.clock()
        observed = self.inspect()
        guest_now = observed.get('clockMs')
        if type(guest_now) is not int or guest_now < 0:
            raise ControlUnconfirmed('GUEST_CLOCK_UNAVAILABLE')
        if observed.get('lease') is not None:
            previous = self.validate(observed['lease'])
            if previous['stopped'] or previous['sequence'] >= sequence:
                raise ControlUnconfirmed('GUEST_RENEWAL_REQUIRES_RECONCILIATION')
        deadline = authority()
        now = self.clock()
        if type(deadline) not in (int, float) or not math.isfinite(deadline) or not math.isfinite(now) or now < start:
            raise ControlUnconfirmed('EXECUTION_AUTHORITY_UNAVAILABLE')
        # Anchoring to the earlier guest sample only shortens a valid lease;
        # arriving late cannot extend it relative to the owner's deadline.
        ttl = min(20000, math.floor((deadline - now - (now - start)) * 1000) - 500)
        if ttl < 1:
            raise ControlUnconfirmed('EXECUTION_AUTHORITY_EXPIRED')
        body = dict(sequence=sequence, ttlMs=ttl, notAfterMs=guest_now + ttl)
        result = self.validate(self.request('POST', '/renew', body).get('lease'))
        after = self.clock()
        if (result['stopped'] or any(result[k] != body[k] for k in body)
                or result['expiresAt'] > body['notAfterMs'] or not math.isfinite(after)
                or after < now or after >= deadline
                or result['expiresAt'] <= guest_now + math.ceil((after - start) * 1000)):
            raise ControlUnconfirmed('GUEST_RENEWAL_UNCONFIRMED')
        return result

    def revoke(self):
        self.inspect()  # Check even an empty guest before creating its tombstone.
        result = self.validate(self.request('POST', '/revoke', {}).get('lease'))
        if not result['stopped']:
            raise ControlUnconfirmed('GUEST_REVOCATION_UNCONFIRMED')
        return result
