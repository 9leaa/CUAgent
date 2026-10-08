"""Real loopback model HTTP using original Task and simulated raw transport."""
import threading
from unittest.mock import Mock
import pytest
from backend.tests.test_handoff_checked_input import selected
from backend.tests.test_handoff_draft_http import http


@pytest.fixture
def task(selected):
    t, control, _, _, _ = selected
    return t, control, None


def test_http_input_uses_exact_checked_text_and_one_raw(http,selected):
    t, _, _, request = http
    _, _, send, draft, args = selected
    assert request(args,op='type_checked_draft') == (200,{'ok':True})
    assert t.used == 2 and send.call_count == 1
    assert send.call_args.args[1]['text'] == draft['document']
    assert t.document.read_bytes() == b''
    assert request(args,op='type_checked_draft')[0] == 409
    assert t.used == 3 and send.call_count == 1


@pytest.mark.parametrize('fault',['digest','extra_text','mode','session','path','large','snapshot','token',
    'missing_draft','old_op','auth','stop','revoke','budget','unknown','audit'])
def test_http_refusal_budget_and_no_new_gui(http,selected,fault):
    t, control, _, request = http
    _, _, send, _, args = selected
    op, credential = 'type_checked_draft', {}
    if fault == 'digest': args['documentSha256'] = '0'*64
    if fault == 'extra_text': args['text'] = 'replacement'
    if fault == 'mode': args['inputMode'] = 'literal-text'
    if fault == 'session': args['sessionId'] = 'other'
    if fault == 'path': args['path'] = '/tmp/other'
    if fault == 'large': args['documentSha256'] = 'x'*40000
    if fault == 'snapshot': args['snapshot_id'] = 'old'
    if fault == 'token': args['element_token'] = 'other'
    if fault == 'missing_draft': t.validated_draft = None
    if fault == 'old_op': op = 'type_text'
    if fault == 'auth': credential = {'credential':'wrong'}
    if fault == 'stop': assert request({},op='stop')[0] == 200
    if fault == 'revoke': control.revoke()
    if fault == 'budget':
        while t.used < 30: t.charge_rejection('fixture',t.used,'fixture')
    if fault == 'unknown': send.side_effect = TimeoutError('unknown')
    if fault == 'audit': t.record = Mock(side_effect=OSError('disk failure'))
    before = t.used
    assert request(args,op=op,**credential)[0] == (403 if fault=='auth' else 409)
    assert send.call_count == (1 if fault=='unknown' else 0)
    if fault in ('auth','stop','revoke','budget','audit'): assert t.used == before
    else: assert t.used == before+1
    if fault in ('unknown','audit'):
        assert request(args,op=op)[0] == 409
        # UNKNOWN never resends GUI, but a new authenticated rejected request
        # still consumes the original budget until stopped/revoked/exhausted.
        assert t.used == (before+2 if fault=='unknown' else before)
        assert send.call_count == (1 if fault=='unknown' else 0)


def test_stop_during_original_inflight_input_does_not_repeat(http,selected):
    t, _, _, request = http
    _, _, send, _, args = selected
    entered, release = threading.Event(),threading.Event()
    def pending(*_):
        entered.set()
        assert release.wait(2)
        return {'ok':True}
    send.side_effect = pending
    result = []
    worker = threading.Thread(target=lambda:result.append(request(args,op='type_checked_draft')))
    worker.start()
    try:
        assert entered.wait(2)
        assert request({},op='stop')[0] == 200
        assert t.inflight
    finally:
        release.set(); worker.join(3)
    assert not worker.is_alive() and len(result)==1
    assert request(args,op='type_checked_draft')[0] == 409
    assert t.used == 2 and send.call_count == 1 and not t.inflight
