from pathlib import Path
import secrets
import sys
import threading
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm'))
from desktop_control import LeaseController
from desktop_control_http import control_server
from desktop_lease import DesktopTask
from desktop_runtime import DesktopGuestRuntime
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed


@pytest.fixture
def lifecycle(tmp_path):
    run = tmp_path / 'task'
    run.mkdir(mode=0o700)
    controller = LeaseController(run / 'lease.json', run_id='task', owner='worker', epoch=1, clock=lambda: 100)
    token = secrets.token_urlsafe(32)
    runtime = DesktopGuestRuntime(run, controller, model_token=secrets.token_urlsafe(32), control_token=token,
        shared_lock=tmp_path / 'bridge.lock', port=0, loopback_test=True,
        task_factory=lambda directory, **kwargs: DesktopTask(directory, environment=lambda: None, **kwargs))
    server = control_server(controller, token, runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
    thread.start()
    clock = [50.0]
    client = DesktopControlClient(port=server.server_port, token=token, run_id='task', owner='worker', epoch=1,
                                  clock=lambda: clock[0])
    try:
        yield client, runtime, clock
    finally:
        server.shutdown(); server.server_close(); thread.join(3)
        runtime.close()


def test_grant_activate_status_revoke_real_loopback(lifecycle):
    client, runtime, _ = lifecycle
    client.renew(1, lambda: 65)
    assert client.activate(lambda: 65)['active']
    assert client.status()['rawCalls'] == 0
    with pytest.raises(ControlUnconfirmed):
        client.activate(lambda: 65)
    assert client.revoke()['stopped']
    assert client.status()['stopped']
    assert runtime.task.used == 0
    assert client.shutdown()['closed']
    assert runtime.closed


def test_wrong_identity_never_activates(lifecycle):
    client, runtime, _ = lifecycle
    client.identity['owner'] = 'wrong'
    with pytest.raises(ControlUnconfirmed):
        client.activate(lambda: 65)
    assert runtime.task is None
    assert not (runtime.directory / 'guest-activation-intent.json').exists()


def test_shutdown_requires_revocation_idle_and_control_role(lifecycle, monkeypatch):
    client, runtime, _ = lifecycle
    client.renew(1, lambda: 65)
    client.activate(lambda: 65)
    with pytest.raises(ControlUnconfirmed):
        client.request('POST', '/shutdown', {})
    assert not runtime.closed
    client.revoke()
    token = client.token
    client.token = runtime.model_token
    with pytest.raises(ControlUnconfirmed):
        client.request('POST', '/shutdown', {})
    client.token = token
    original = runtime.status
    monkeypatch.setattr(runtime, 'status', lambda: {**original(), 'pendingCalls': 1})
    with pytest.raises(ControlUnconfirmed):
        client.request('POST', '/shutdown', {})
    assert not runtime.closed
    monkeypatch.setattr(runtime, 'status', original)
    assert client.shutdown()['closed']


def test_missing_lease_never_activates(lifecycle):
    client, runtime, _ = lifecycle
    with pytest.raises(ControlUnconfirmed):
        client.activate(lambda: 65)
    assert runtime.task is None
    assert not (runtime.directory / 'guest-activation-intent.json').exists()


@pytest.mark.parametrize('deadline', [50, True, float('nan'), None])
def test_invalid_authority_never_sends_activation(lifecycle, deadline):
    client, runtime, _ = lifecycle
    client.renew(1, lambda: 65)
    with pytest.raises(ControlUnconfirmed):
        client.activate(lambda: deadline)
    assert runtime.task is None


@pytest.mark.parametrize('failure', ['lost', 'late'])
def test_activation_ack_loss_or_delay_is_not_replayed(lifecycle, failure):
    client, runtime, clock = lifecycle
    client.renew(1, lambda: 65)
    original = client.request
    activations = []
    def response(method, path, body=None):
        result = original(method, path, body)
        if path == '/activate':
            activations.append(path)
            if failure == 'lost':
                raise ControlUnconfirmed('lost acknowledgement')
            clock[0] = 66
        return result
    client.request = response
    with pytest.raises(ControlUnconfirmed):
        client.activate(lambda: 65)
    with pytest.raises(ControlUnconfirmed):
        client.activate(lambda: 80)
    assert activations == ['/activate']
    assert runtime.status()['active']
    client.request = original
    assert client.revoke()['stopped']


def test_malformed_or_regressing_status_rejected(lifecycle):
    client, _, _ = lifecycle
    original = client.status()
    for change in [{'rawCalls': True}, {'pendingCalls': 1}, {'active': 1},
                   {'active': True, 'modelPort': None}, {'modelPort': True}, {'rawCalls': 31}]:
        with pytest.raises(ControlUnconfirmed):
            client.validate_status({**original, **change})
    client.validate_status({**original, 'rawCalls': 2})
    with pytest.raises(ControlUnconfirmed):
        client.validate_status({**original, 'rawCalls': 1})
