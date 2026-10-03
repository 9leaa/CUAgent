from pathlib import Path
import secrets
import sys
import threading
from unittest.mock import Mock
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm'))
from desktop_control import LeaseController
from desktop_control_http import control_server
from backend.desktop_client import ControlUnconfirmed, DesktopControlClient


@pytest.fixture
def channel(tmp_path):
    guest = [100.0]
    controller = LeaseController(tmp_path / 'lease.json', run_id='task', owner='owner', epoch=1, clock=lambda: guest[0])
    token = secrets.token_urlsafe(32)
    server = control_server(controller, token)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
    thread.start()
    client = DesktopControlClient(port=server.server_address[1], token=token,
                                  run_id='task', owner='owner', epoch=1, clock=lambda: 50.0)
    yield client, controller, guest
    server.shutdown(); server.server_close(); thread.join(3)


def test_real_transport_authority_grant_gate_and_revoke(channel):
    client, controller, guest = channel
    authority = Mock(return_value=65.0)
    record = client.renew(1, authority)
    assert record['expiresAt'] == 114500
    authority.assert_called_once()
    controller.gate.check()
    assert client.revoke()['stopped'] is True
    with pytest.raises(ControlUnconfirmed): client.renew(2, authority)
    authority.assert_called_once()  # Stopped guest rejected before any new authority.


def test_delayed_initial_post_cannot_create_fresh_lease(channel):
    client, controller, guest = channel
    def authority():
        guest[0] = 120
        return 65.0
    with pytest.raises(ControlUnconfirmed): client.renew(1, authority)
    assert not controller.path.exists()


def test_expired_or_failed_authority_never_sends_grant(channel):
    client, controller, _ = channel
    for deadline in (50, 50.1, True, float('nan'), None):
        with pytest.raises(ControlUnconfirmed): client.renew(1, lambda: deadline)
    with pytest.raises(RuntimeError, match='DB unavailable'):
        client.renew(1, Mock(side_effect=RuntimeError('DB unavailable')))
    assert not controller.path.exists()


def test_identity_mismatch_and_same_sequence_require_reconciliation(channel):
    client, controller, _ = channel
    client.renew(1, lambda: 65)
    before = controller.path.read_bytes()
    with pytest.raises(ControlUnconfirmed): client.renew(1, lambda: 70)
    client.identity['owner'] = 'other'
    with pytest.raises(ControlUnconfirmed): client.renew(2, lambda: 70)
    assert controller.path.read_bytes() == before


def test_response_loss_does_not_automatically_retry_mutation(channel):
    client, controller, _ = channel
    original = client.request
    calls = []
    def dropped(method, path, body=None):
        calls.append(path)
        response = original(method, path, body)
        if path == '/renew':
            raise ControlUnconfirmed('lost response')
        return response
    client.request = dropped
    with pytest.raises(ControlUnconfirmed): client.renew(1, lambda: 65)
    assert calls == ['/lease', '/renew']
    assert controller.existing()['sequence'] == 1
    client.request = original
    assert client.revoke()['stopped'] is True


def test_delayed_ack_cannot_be_reported_as_current_permission(channel):
    client, controller, _ = channel
    times = iter([50.0, 50.0, 66.0])
    client.clock = lambda: next(times)
    with pytest.raises(ControlUnconfirmed): client.renew(1, lambda: 65)
    assert controller.existing()['expiresAt'] == 114500


def test_wrong_binding_cannot_mutate_even_an_empty_guest(channel):
    client, controller, _ = channel
    client.identity['runId'] = 'other'
    with pytest.raises(ControlUnconfirmed): client.renew(1, lambda: 65)
    with pytest.raises(ControlUnconfirmed): client.revoke()
    assert not controller.path.exists()
