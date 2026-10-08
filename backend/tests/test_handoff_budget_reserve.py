"""Original ledger/reopen/submit with simulated GUI, not business acceptance."""
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from backend.tests.test_handoff_draft_task import task
from driver_smoke import StopRun


def saved(task, used):
    t, _, report = task
    body = t.check_draft({'raw': json.dumps(report)})['document']
    t.document.write_text(body)
    t.input_once = t.saved_once = True
    t.pid, t.window = 10, 20
    while t.used < used:
        t.charge_rejection('fixture-padding', t.used, 'fixture-only')
    def state():
        return dict(snapshot_id='fresh', pid=10, window_id=t.window,
            window_title=t.case.title, app_name='TextEdit',
            tree_markdown='- AXWindow\n  - AXTextArea = ' + json.dumps(body),
            screenshot_frame_valid=True, window_bounds=dict(x=70, y=48),
            elements=[dict(role='AXWindow', label=t.case.title, element_index=0),
                dict(role='AXButton', label='', element_index=6, element_token='fresh:6',
                    parent_index=0, enabled=True, actions=['AXPress'],
                    frame=dict(x=76, y=54, w=16, h=16))])
    t.snapshot = state()
    t.observed_at = time.monotonic()
    t.document_opener = Mock(return_value=True)
    return t, report, body, state


@pytest.mark.parametrize('task,used', [('legacy-final-json', 20), ('p7-tool-submit-v1', 19)], indirect=['task'])
def test_insufficient_reserve_rejects_before_any_side_effect(task, used):
    t, _, _, _ = saved(task, used)
    t.transport = Mock(side_effect=AssertionError('unexpected GUI'))
    with pytest.raises(StopRun):
        t.reopen({'snapshot_id': 'fresh'})
    t.transport.assert_not_called()
    t.document_opener.assert_not_called()
    assert not (t.directory/'handoff-reopen-intent.json').exists()
    assert t.used == used  # HTTP owns rejected-request charging, not this method.


@pytest.mark.parametrize('task,used', [('legacy-final-json', 19), ('p7-tool-submit-v1', 18)], indirect=['task'])
def test_worst_case_window_queries_leave_budget_for_complete_tail(task, used):
    t, report, body, state = saved(task, used)
    def window(i):
        return dict(pid=10, window_id=i, title=t.case.title, app_name='TextEdit', is_on_screen=True)
    inventories = iter([[window(20)], [window(20)], [], [], [], [window(21)]])
    calls = []
    def transport(tool, args):
        calls.append(tool)
        if tool == 'list_windows':
            return {'windows': next(inventories)}
        if tool == 'get_window_state':
            Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            return state()
        assert tool == 'click'
        return {'ok': True}
    t.transport = transport
    with patch('handoff_task.time.sleep'):
        t.reopen({'snapshot_id': 'fresh'})
    assert t.used == used + 8
    t.observe()
    t.write_result({'snapshot_id': 'fresh', 'value': body})
    assert t.read_result()['content'] == body + '\n'
    if t.submission_protocol == 'p7-tool-submit-v1':
        assert t.used == 29
        assert t.submit_handoff({'report': report})['status'] == 'HANDOFF_SUBMITTED'
        assert t.submission_terminal
    assert t.used == 30
    assert calls.count('click') == 1 and calls.count('list_windows') == 6
    t.document_opener.assert_called_once()
    with pytest.raises(StopRun):
        t.read_result()
    assert t.used == 30
