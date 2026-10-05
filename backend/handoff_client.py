"""Trusted P7 transfer/activation; never invokes a model or invents authority."""
import base64
import hashlib
import math
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical


class HandoffControlClient(DesktopControlClient):
    def activation_request(self):
        receipt = getattr(self, '_input_receipt', None)
        if receipt is None or receipt['binding'] != self.identity:
            raise ControlUnconfirmed('HANDOFF_INPUT_NOT_CONFIRMED')
        return '/activate-handoff', {'inputSha256': receipt['inputSha256']}

    def provision_handoff(self, submission, authority):
        with self._lifecycle_lock:
            if getattr(self, '_input_attempted', False):
                raise ControlUnconfirmed('HANDOFF_INPUT_REQUIRES_RECONCILIATION')
            submission = HandoffSubmission.model_validate(submission)
            raw = canonical(submission.model_dump(mode='json'))
            digest = hashlib.sha256(raw).hexdigest()
            self._input_attempted = True
            start = self.clock()
            state = self.status()
            if state['active'] or state['stopped'] or state['rawCalls'] or state['pendingCalls']:
                raise ControlUnconfirmed('GUEST_RUNTIME_NOT_FRESH')
            observed = self.inspect()
            lease = self.validate(observed.get('lease'))
            guest_now = observed.get('clockMs')
            if type(guest_now) is not int or guest_now < 0 or lease['stopped'] or guest_now >= lease['expiresAt']:
                raise ControlUnconfirmed('HANDOFF_INPUT_LEASE_UNAVAILABLE')
            deadline = authority()
            def check(now):
                if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                        or not math.isfinite(start) or not math.isfinite(now) or now < start or now >= deadline
                        or guest_now + math.ceil((now - start) * 1000) >= lease['expiresAt']):
                    raise ControlUnconfirmed('HANDOFF_INPUT_AUTHORITY_UNAVAILABLE')
            check(self.clock())
            body = dict(binding=self.identity, inputSha256=digest, inputBase64=base64.b64encode(raw).decode('ascii'))
            result = self.request('POST', '/handoff-input', body)
            check(self.clock())
            expected = dict(status='STORED', binding=self.identity, inputSha256=digest, bytes=len(raw))
            if (result != expected or type(result.get('bytes')) is not int
                    or type(result.get('binding', {}).get('version')) is not int
                    or type(result.get('binding', {}).get('epoch')) is not int):
                raise ControlUnconfirmed('HANDOFF_INPUT_ACK_MISMATCH')
            self._input_receipt = dict(result, binding=dict(result['binding']))
            return result
