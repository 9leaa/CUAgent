"""Trusted P7 transfer/activation; never invokes a model or invents authority."""
import base64
import hashlib
import math
import re
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical


class HandoffControlClient(DesktopControlClient):
    def bind_draft_session(self, session_id):
        with self._lifecycle_lock:
            if (self._activation_attempted
                    or getattr(self, '_draft_session_id', None) is not None
                    or type(session_id) is not str
                    or not re.fullmatch(r'session-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',session_id)):
                raise ControlUnconfirmed('HANDOFF_SESSION_BINDING_REQUIRED')
            self._draft_session_id = session_id

    def activation_request(self):
        receipt = getattr(self, '_input_receipt', None)
        if receipt is None or receipt['binding'] != self.identity:
            raise ControlUnconfirmed('HANDOFF_INPUT_NOT_CONFIRMED')
        body = {'inputSha256': receipt['inputSha256']}
        if getattr(self, '_draft_session_id', None) is not None:
            body['sessionId'] = self._draft_session_id
        return '/activate-handoff', body

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
