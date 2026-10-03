from datetime import timedelta
import json
from pathlib import Path
import secrets
import sys
import threading
import time
from unittest.mock import Mock
import uuid
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm'))
from desktop_control import LeaseController
from desktop_control_http import control_server
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed
from backend.desktop_execution_control import DesktopExecutionControl
from backend.models import Resource, Task, utcnow
from backend.service import Conflict


@pytest.fixture
def execution(service, tmp_path):
    identity, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['test handoff']}, 'desktop')
    task = service.claim(str(uuid.uuid4()), kind='desktop-textedit')
    guest = tmp_path / 'guest'; guest.mkdir(mode=0o700)
    controller = LeaseController(guest / 'lease.json', run_id='p2-' + identity,
                                 owner=task.owner, epoch=task.epoch, clock=time.time)
    token = secrets.token_urlsafe(32)
    server = control_server(controller, token)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
    thread.start()
    client = DesktopControlClient(port=server.server_address[1], token=token,
                                  run_id='p2-' + identity, owner=task.owner, epoch=task.epoch)
    control = DesktopExecutionControl(service, client, task_id=identity, owner=task.owner, epoch=task.epoch)
    yield task, controller, client, control
    server.shutdown(); server.server_close(); thread.join(3)


def test_pg_authority_http_lease_and_stop_are_connected(service, execution):
    task, guest, client, control = execution
    first = control.refresh()
    assert first['sequence'] == 1 and first['stopped'] is False
    guest.gate.check()
    assert control.refresh()['sequence'] == 2
    assert service.stop(task.id) == 'STOP_REQUESTED'
    with pytest.raises(ControlUnconfirmed): control.refresh()
    assert control.closed and control.local_revoked and control.guest_revoked
    assert guest.existing()['stopped'] is True
    local = json.loads((service.settings.root / 'controls' / (task.id + '.json')).read_text())
    assert local['stopped'] is True
    assert control.close()['inflightCancellationConfirmed'] is False
    with pytest.raises(ControlUnconfirmed): control.refresh()


@pytest.mark.parametrize('fault', ['task-owner', 'task-epoch', 'resource-owner', 'resource-epoch', 'expired', 'wrong-kind'])
def test_authority_rejects_wrong_owner_epoch_type_or_expiry(service, execution, fault):
    task, guest, client, control = execution
    with service.sessions.begin() as db:
        stored, resource = db.get(Task, task.id), db.get(Resource, 'desktop')
        if fault == 'task-owner': stored.owner = str(uuid.uuid4())
        if fault == 'task-epoch': stored.epoch += 1
        if fault == 'resource-owner': resource.owner = str(uuid.uuid4())
        if fault == 'resource-epoch': resource.epoch += 1
        if fault == 'expired': resource.expires_at = utcnow() - timedelta(seconds=1)
        if fault == 'wrong-kind': stored.payload = {'date': '2026-10-03'}
    with pytest.raises(Conflict):
        service.desktop_authority(task.id, task.owner, task.epoch)
    assert not guest.path.exists()


def test_database_remaining_lifetime_caps_monotonic_deadline(service, execution):
    task, _, _, _ = execution
    with service.sessions.begin() as db:
        db.get(Resource, 'desktop').expires_at = utcnow() + timedelta(seconds=3)
    deadline = service.desktop_authority(task.id, task.owner, task.epoch, clock=lambda: 100)
    assert 100 < deadline <= 103


def test_authority_failure_after_heartbeat_closes_both_gates(service, execution):
    task, guest, client, control = execution
    control.refresh()
    service.desktop_authority = Mock(side_effect=RuntimeError('database unavailable'))
    with pytest.raises(ControlUnconfirmed): control.refresh()
    assert control.local_revoked and control.guest_revoked
    assert guest.existing()['stopped']
    service.desktop_authority.assert_called_once()
    with pytest.raises(ControlUnconfirmed): control.refresh()
    service.desktop_authority.assert_called_once()


def test_unreachable_guest_preserves_unconfirmed_revocation(service, execution):
    task, guest, client, control = execution
    control.refresh()
    client.request = Mock(side_effect=ControlUnconfirmed('unreachable'))
    with pytest.raises(ControlUnconfirmed): control.refresh()
    assert control.local_revoked and not control.guest_revoked and control.closed
    # A network failure is not permission to forge a successful guest stop.
    assert not guest.existing()['stopped']
    count = client.request.call_count
    with pytest.raises(ControlUnconfirmed): control.refresh()
    assert client.request.call_count == count


def test_mismatched_client_cannot_construct_execution_control(service, execution):
    task, _, client, _ = execution
    with pytest.raises(ValueError):
        DesktopExecutionControl(service, client, task_id='other', owner=task.owner, epoch=task.epoch)
