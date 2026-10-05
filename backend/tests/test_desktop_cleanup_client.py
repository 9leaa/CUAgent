from unittest.mock import Mock
import pytest
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed


@pytest.fixture
def cleanup():
    client = DesktopControlClient(port=19001, token='c' * 43, run_id='task', owner='owner', epoch=1)
    state = dict(binding=client.identity, active=True, stopped=True, rawCalls=12, pendingCalls=0, modelPort=8766)
    client.status = Mock(return_value=state)
    hashes = dict(document='a' * 64, result='b' * 64, trace='c' * 64)
    receipt = dict(client.identity, pid=123, startedUs=1790000000123456,
        executable='/System/Applications/TextEdit.app/Contents/MacOS/TextEdit', verifiedHashes=hashes,
        status='EXITED', reason='PROCESS_ABSENT', terminationRequested=True, forced=False)
    client.request = Mock(return_value=receipt)
    return client, hashes, receipt, state


def test_valid_receipt_checked_with_single_long_request(cleanup):
    client, hashes, receipt, _ = cleanup
    assert client.cleanup_application(hashes) == receipt
    client.request.assert_called_once_with('POST', '/cleanup-app',
        {'sessionTerminal': True, 'sessionVerified': True, 'hashes': hashes}, timeout=60)
    assert client.status.call_count == 2
    with pytest.raises(ControlUnconfirmed): client.cleanup_application(hashes)
    client.request.assert_called_once()


@pytest.mark.parametrize('field,value', [('epoch', True), ('runId', 'other'), ('pid', True),
    ('startedUs', 0), ('forced', True), ('verifiedHashes', {}), ('executable', '/other'),
    ('reason', 'EXIT_NOT_CONFIRMED'), ('terminationRequested', False), ('status', 'SUCCEEDED')])
def test_mismatched_or_false_success_receipt_rejected(cleanup, field, value):
    client, hashes, receipt, _ = cleanup
    receipt[field] = value
    with pytest.raises(ControlUnconfirmed): client.cleanup_application(hashes)
    client.request.assert_called_once()


def test_unknown_response_no_retry(cleanup):
    client, hashes, _, _ = cleanup
    client.request.side_effect = ControlUnconfirmed('lost ack')
    with pytest.raises(ControlUnconfirmed): client.cleanup_application(hashes)
    with pytest.raises(ControlUnconfirmed): client.cleanup_application(hashes)
    client.request.assert_called_once()


def test_rejected_cleanup_preserved_not_relabelled_success(cleanup):
    client, hashes, receipt, _ = cleanup
    receipt.update(status='REFUSED', reason='PRECONDITION_FAILED', terminationRequested=False)
    assert client.cleanup_application(hashes)['status'] == 'REFUSED'


def test_budget_drift_after_exit_rejected(cleanup):
    client, hashes, _, state = cleanup
    client.status.side_effect = [state, dict(state, rawCalls=13)]
    with pytest.raises(ControlUnconfirmed): client.cleanup_application(hashes)


@pytest.mark.parametrize('change', [{'stopped': False}, {'pendingCalls': 1}])
def test_not_stopped_idle_never_dispatches(cleanup, change):
    client, hashes, _, state = cleanup
    state.update(change)
    with pytest.raises(ControlUnconfirmed): client.cleanup_application(hashes)
    client.request.assert_not_called()
