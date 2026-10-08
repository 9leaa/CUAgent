"""Authenticated real loopback HTTP; simulated lifecycle, no model/GUI."""
import pytest
from backend.tests.test_handoff_draft_http import http
from backend.tests.test_handoff_draft_task import task
from backend.tests.test_handoff_submit_task import prepared


@pytest.mark.parametrize('task', ['p7-tool-submit-v1'], indirect=True)
def test_full_submission_http_is_counted_and_terminal(http):
    t, c, report, request = http
    prepared((t, c, report))
    code, value = request({'report': report}, op='submit_handoff')
    assert code == 200 and value['status'] == 'HANDOFF_SUBMITTED' and value['used'] == 3
    assert not value['semanticVerified'] and not value['guiVerified']
    for op, args in [('submit_handoff', {'report': report}), ('read_result', {}),
                     ('check_draft', {'raw': '{}'}), ('type_text', {'text': 'after'})]:
        assert request(args, op=op)[0] == 409
        assert t.used == 3 and not t.inflight


@pytest.mark.parametrize('task', ['p7-tool-submit-v1'], indirect=True)
@pytest.mark.parametrize('fault', ['missing_read', 'report', 'protocol_arg', 'large', 'bad_auth', 'stop', 'revoke'])
def test_submission_refusal_original_admission(http, fault):
    t, c, report, request = http
    prepared((t, c, report)); args = {'report': report}
    if fault == 'missing_read': t.result_readback = None
    if fault == 'report': report['tasks'][0]['progress']['text'] = 'changed'
    if fault == 'protocol_arg': args['protocol'] = 'p7-tool-submit-v1'
    if fault == 'large': report['extra'] = 'x' * 65537
    if fault == 'stop': assert request({}, op='stop')[0] == 200
    if fault == 'revoke': c.revoke()
    code, _ = request(args, op='submit_handoff', **({'credential': 'wrong'} if fault == 'bad_auth' else {}))
    assert code == (403 if fault == 'bad_auth' else 409)
    assert t.used == (2 if fault in ('bad_auth', 'stop', 'revoke') else 3)
    assert not t.submission_terminal and not t.inflight


def test_legacy_handoff_does_not_gain_tool_or_method_authority(http):
    t, c, report, request = http
    prepared((t, c, report))
    assert t.submission_protocol == 'legacy-final-json'
    assert request({'report': report}, op='submit_handoff')[0] == 409
    assert t.used == 3 and not t.submission_terminal
    from driver_smoke import StopRun
    with pytest.raises(StopRun): t.submit_handoff({'report': report})
    assert t.used == 4 and not t.submission_terminal
