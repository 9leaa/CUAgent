"""Original Task admission/audit with simulated lifecycle; no real GUI proof."""
import hashlib
import json
from unittest.mock import patch

import pytest
from backend.tests.test_handoff_draft_task import task
from driver_smoke import StopRun
from handoff_task import HandoffDesktopTask
from backend.tests.test_handoff_result import SESSION

pytestmark = pytest.mark.parametrize('task', ['p7-tool-submit-v1'], indirect=True)


def prepared(task):
    t, controller, report = task
    draft = t.check_draft({'raw': json.dumps(report)})
    body = draft['document']
    t.document.write_bytes(body.encode())
    t.input_once = t.saved_once = t.reopened = t.result_written = True
    t.reopen_phase = 'reopened'
    t.reopen_digest = hashlib.sha256(body.encode()).hexdigest()
    (t.directory / 'result.txt').write_text(body + '\n')
    assert t.read_result()['content'] == body + '\n'
    return t, controller, report


def test_commit_is_audited_counted_and_terminal(task):
    t, _, report = prepared(task)
    response = t.submit_handoff({'report': report})
    assert response['status'] == 'HANDOFF_SUBMITTED' and response['used'] == 3
    assert response['semanticVerified'] is response['guiVerified'] is False
    rows = [json.loads(line) for line in t.ledger.read_text().splitlines()]
    args = next(r for r in rows if r.get('tool') == 'submit_handoff' and r['event'] == 'helper_arguments')
    result = next(r for r in rows if r.get('tool') == 'submit_handoff' and r['event'] == 'result')
    assert args['args'] == {'report': report} and args['call_id'] == result['call_id']
    for call in [lambda: t.submit_handoff({'report': report}), t.read_result, t.read_materials,
                 lambda: t.admit('type_text')]:
        with pytest.raises(StopRun): call()
    assert t.used == 3 and not t.inflight


@pytest.mark.parametrize('mode', ['input', 'saved', 'reopen', 'written', 'read', 'session',
                                 'report', 'document', 'result', 'link', 'intervening'])
def test_missing_or_tampered_evidence_refused_and_counted(task, mode):
    t, _, report = prepared(task)
    if mode == 'input': t.input_once = False
    if mode == 'saved': t.saved_once = False
    if mode == 'reopen': t.reopened = False
    if mode == 'written': t.result_written = False
    if mode == 'read': t.result_readback = None
    if mode == 'session': t.draft_session_id = None
    if mode == 'report': report['tasks'][0]['progress']['text'] = 'replaced'
    if mode == 'document': t.document.write_bytes(b'changed')
    if mode == 'result': (t.directory / 'result.txt').write_bytes(b'changed')
    if mode == 'link':
        (t.directory / 'result.txt').unlink()
        (t.directory / 'result.txt').symlink_to(t.document)
    if mode == 'intervening': t.read_materials()
    before = t.used
    with pytest.raises((StopRun, OSError)): t.submit_handoff({'report': report})
    assert t.used == before + 1 and not t.submission_terminal and not t.inflight


@pytest.mark.parametrize('mode', ['stop', 'revoke', 'budget'])
def test_denied_admission_never_dispatches(task, mode):
    t, c, report = prepared(task)
    if mode == 'stop': t.stop()
    if mode == 'revoke': c.revoke()
    if mode == 'budget':
        for _ in range(28): t.read_result()
    before = t.used
    with pytest.raises(StopRun): t.submit_handoff({'report': report})
    assert t.used == before and not t.submission_terminal and not t.inflight


@pytest.mark.parametrize('mode', ['stop', 'revoke'])
def test_stop_or_revocation_during_validation_cannot_commit(task, mode):
    t, c, report = prepared(task)
    original = t._read_frozen_input
    def interrupted():
        t.stop() if mode == 'stop' else c.revoke()
        return original()
    t._read_frozen_input = interrupted
    with pytest.raises(StopRun): t.submit_handoff({'report': report})
    assert t.used == 3 and not t.submission_terminal and not t.inflight
    assert not any(r.get('tool') == 'submit_handoff' and r['event'] == 'result'
                   for r in map(json.loads, t.ledger.read_text().splitlines()))


def test_audit_write_failure_locks_terminal(task):
    t, _, report = prepared(task)
    original = t.record
    def failing(row):
        if row['event'] == 'result' and row.get('tool') == 'submit_handoff':
            raise OSError('injected audit failure')
        original(row)
    with patch.object(t, 'record', side_effect=failing):
        with pytest.raises(OSError): t.submit_handoff({'report': report})
    assert t.submission_terminal and t.stopped.is_set() and not t.inflight
    with pytest.raises(StopRun): t.read_result()


def test_restart_retains_budget_and_never_resumes_submission(task):
    t, c, report = prepared(task)
    t.submit_handoff({'report': report})
    restarted = HandoffDesktopTask(t.directory, lambda *_: pytest.fail('GUI'), lambda _: None,
        lease=c.gate, approved=True, environment=lambda: None,
        input_sha256=t.input_sha256, draft_session_id=SESSION)
    with pytest.raises(StopRun): restarted.submit_handoff({'report': report})
    assert restarted.used == 3 and restarted.stopped.is_set()
