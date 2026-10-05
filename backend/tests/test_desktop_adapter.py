from dataclasses import replace
from contextlib import nullcontext
import errno
import hashlib
import json
import socket
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from backend.desktop_adapter import DesktopAdapterSettings, DesktopTaskAdapter
from backend.desktop_collect import save_exclusive
from backend.desktop_worker import DesktopWorker


@pytest.fixture
def assembled(tmp_path):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        tunnel_port = probe.getsockname()[1]
    for name, mode in [('known-hosts', 0o600), ('askpass', 0o700)]:
        path = tmp_path / name
        path.write_text('synthetic')
        path.chmod(mode)
    service = Mock()
    service.settings.root = tmp_path
    task = SimpleNamespace(id='11111111-1111-1111-1111-111111111111', owner='22222222-2222-2222-2222-222222222222',
                           epoch=1, payload={'kind': 'desktop-textedit', 'lines': ['synthetic']})
    settings = DesktopAdapterSettings(node=tmp_path / 'node', official_home=tmp_path / 'home', cookie=tmp_path / 'cookie',
        build_tools=tmp_path / 'tools', base_tasks=tmp_path / 'tasks',
        known_hosts=tmp_path / 'known-hosts', askpass=tmp_path / 'askpass',
        guest_commit='a' * 40, guest_manifest_sha='b' * 64, tunnel_port=tunnel_port, cutover_authorized=True)
    gate = Mock(return_value=True)
    adapter = DesktopTaskAdapter(service, settings, execution_gate=gate)
    adapter.command = Mock()
    with patch('backend.desktop_adapter.DesktopSessionClient') as session, \
            patch('backend.desktop_adapter.DesktopControlClient') as client, \
            patch('backend.desktop_adapter.GuestControlTunnel') as tunnel, \
            patch('backend.desktop_adapter.bootstrap_guest', return_value={'controlToken': 'c' * 43,
                'modelToken': 'm' * 43, 'controlPort': 20001, 'modelUrl': 'http://192.168.64.3:8766'}):
        yield adapter, task, session.return_value, client.return_value, tunnel.return_value, gate


def test_composed_prepare_start_verify_restore_with_mock_edges(assembled):
    adapter, task, session, client, tunnel, gate = assembled
    prepared = adapter.prepare(task)
    client.activate.assert_not_called()
    session.start.assert_not_called()


    adapter.start(prepared)
    assert [call.args[2] for call in adapter.command.call_args_list] == ['prepare', 'stop-activate', 'apply', 'start-p6']
    client.activate.assert_called_once()
    session.start.assert_called_once()
    assert gate.call_count == 3
    with pytest.raises(RuntimeError): adapter.start(prepared)
    bundle = {'files': {'artifacts/handoff-' + prepared.run.name + '.txt': b'synthetic\n',
                        'result.txt': b'synthetic\n\n', 'trace.jsonl': b'synthetic trace'}, 'guest': {'rawCalls': 12}}
    with patch('backend.desktop_adapter.collect_guest_bundle', return_value=bundle), \
            patch('backend.desktop_adapter.verify_desktop_session', return_value={'sessionVerified': True}):
        result = adapter.verify(prepared)
    assert result['status'] == 'SUCCEEDED'
    assert (prepared.run / 'workspace/document.txt').read_bytes() == b'synthetic\n'
    client.cleanup_application.return_value = {'status': 'EXITED'}  # Client receipt validation tested separately.
    adapter.restore(prepared)
    client.cleanup_application.assert_called_once_with({
        'document': hashlib.sha256(b'synthetic\n').hexdigest(),
        'result': hashlib.sha256(b'synthetic\n\n').hexdigest(),
        'trace': hashlib.sha256(b'synthetic trace').hexdigest()})
    client.shutdown.assert_called_once()
    tunnel.close.assert_called_once()
    assert [call.args[2] for call in adapter.command.call_args_list][-3:] == ['stop-restore', 'restore', 'start-restore']


def test_selected_port_persisted_before_bootstrap_and_used_by_client(assembled):
    adapter, task, session, client, tunnel, _ = assembled
    root = adapter.service.settings.root / ('p2-' + task.id)
    def bootstrap(**kwargs):
        path = root / 'desktop-tunnel-selection.json'
        assert path.stat().st_mode & 0o777 == 0o600
        assert json.loads(path.read_text()) == {
            'binding': {'version': 1, 'runId': root.name, 'owner': task.owner, 'epoch': task.epoch},
            'preferredPort': adapter.settings.tunnel_port, 'hostPort': 19123}
        return {'controlToken': 'c' * 43, 'modelToken': 'm' * 43,
                'controlPort': 20001, 'modelUrl': 'http://192.168.64.3:8766'}
    with patch('backend.desktop_adapter.select_tunnel_port', return_value=19123) as select, \
            patch('backend.desktop_adapter.bootstrap_guest', side_effect=bootstrap) as start, \
            patch('backend.desktop_adapter.DesktopControlClient', return_value=client) as constructor:
        adapter.prepare(task)
        select.assert_called_once_with(adapter.settings.tunnel_port)
        start.assert_called_once()
        assert constructor.call_args.kwargs['port'] == 19123
        tunnel.start.assert_called_once()
        session.start.assert_not_called()


def test_unverified_task_restore_skips_app_cleanup_with_warning(assembled):
    adapter, task, _, client, tunnel, _ = assembled
    prepared = adapter.prepare(task)
    adapter.restore(prepared)
    client.cleanup_application.assert_not_called()
    client.shutdown.assert_called_once()
    tunnel.close.assert_called_once()
    record = json.loads((prepared.run / 'desktop-app-cleanup-skipped.json').read_text())
    assert record['applicationMayRemain'] is True


@pytest.mark.parametrize('outcome', ['REFUSED', 'UNKNOWN', 'exception'])
def test_cleanup_failure_retains_warning_and_does_not_shutdown_or_replay(assembled, outcome):
    adapter, task, _, client, tunnel, _ = assembled
    prepared = adapter.prepare(task)
    adapter.context(prepared)['verified_cleanup_hashes'] = dict(document='a' * 64, result='b' * 64, trace='c' * 64)
    if outcome == 'exception':
        client.cleanup_application.side_effect = RuntimeError('private transport details')
    else:
        client.cleanup_application.return_value = {'status': outcome}
    with pytest.raises(RuntimeError): adapter.restore(prepared)
    assert [call.args[2] for call in adapter.command.call_args_list][-3:] == ['stop-restore', 'restore', 'start-restore']
    client.shutdown.assert_not_called(); tunnel.close.assert_not_called()
    warning = (prepared.run / 'desktop-app-cleanup-warning.json').read_text()
    assert 'private transport' not in warning
    assert json.loads(warning)['retryAllowed'] is False
    with pytest.raises(FileExistsError): adapter.restore(prepared)
    client.cleanup_application.assert_called_once()


def test_selection_exhaustion_never_bootstraps_or_creates_session(assembled):
    adapter, task, session, _, tunnel, _ = assembled
    with patch('backend.desktop_adapter.select_tunnel_port', side_effect=OSError(errno.EADDRINUSE, 'busy')), \
            patch('backend.desktop_adapter.bootstrap_guest') as start:
        with pytest.raises(OSError): adapter.prepare(task)
        start.assert_not_called()
        tunnel.start.assert_not_called()
        session.start.assert_not_called()
    assert adapter.cleaned_preparations[task.id] == (
        task, adapter.service.settings.root / ('p2-' + task.id), 'not-started')
    with patch('backend.desktop_adapter.confirm_preparation_closed', return_value='proof') as confirm:
        assert adapter.confirm_prepare_failure(task) == 'proof'
        assert confirm.call_args.kwargs['guest_state'] == 'not-started'


@pytest.mark.parametrize('profile_changed', [False, True])
def test_real_adapter_worker_preflight_failure_in_isolated_database(assembled, service, profile_changed):
    # Real adapter/Worker/proof/DB; only lifecycle command and external edges mocked.
    adapter, _, session, client, tunnel, _ = assembled
    adapter.service = service
    home = adapter.settings.official_home
    (home / 'profiles/desktop').mkdir(parents=True, mode=0o700)
    home.chmod(0o700)
    target = home / 'profiles/desktop/cordis.patch.yml'
    before = b'[]\n'
    save_exclusive(target, before)
    def profile_prepare(root, group, mode):
        assert (group, mode) == ('profile', 'prepare')
        save_exclusive(root / 'profile-before.yml', before)
        save_exclusive(root / 'profile-plan.json', json.dumps(dict(version=1,
            root=str(root), home=str(home), target=str(target),
            beforeSha256=hashlib.sha256(before).hexdigest())).encode())
        if profile_changed: target.write_bytes(b'changed')
    adapter.command.side_effect = profile_prepare
    task_id, _ = service.submit({'kind': 'desktop-textedit', 'lines': ['synthetic']}, 'adapter-preflight')
    worker = DesktopWorker(service, adapter, shared_lock=service.settings.root / 'desktop-worker.lock')
    with patch('backend.desktop_adapter.select_tunnel_port', side_effect=OSError(errno.EADDRINUSE, 'busy')), \
            patch('backend.desktop_adapter.bootstrap_guest') as bootstrap:
        result = worker.run_once(task_id=task_id)
        bootstrap.assert_not_called()
    assert result['quarantined'] is profile_changed
    assert result['status'] == ('BLOCKED' if profile_changed else 'FAILED')
    assert result['usage'] == {'available': False}
    if not profile_changed:
        assert result['guestNotStarted'] and not result['revocation']['guestRevoked']
        assert not result['preparationCleanupConfirmed'] and result['restoreConfirmed']
        assert service.view(task_id)['status'] == 'FAILED'
        assert not worker.quarantine.exists()
    session.start.assert_not_called()
    client.activate.assert_not_called()
    client.revoke.assert_not_called()
    tunnel.start.assert_not_called()
    adapter.command.assert_called_once()


def test_post_selection_tunnel_failure_never_reselects_or_relaunches(assembled):
    adapter, task, session, _, tunnel, _ = assembled
    tunnel.start.side_effect = OSError(errno.EADDRINUSE, 'late race')
    with patch('backend.desktop_adapter.select_tunnel_port', return_value=19123) as select, \
            patch('backend.desktop_adapter.cleanup_prepared_guest') as cleanup:
        with pytest.raises(OSError): adapter.prepare(task)
        select.assert_called_once()
        tunnel.start.assert_called_once()
        cleanup.assert_called_once()
        session.start.assert_not_called()


@pytest.mark.parametrize('cleanup_fails', [False, True])
def test_tunnel_failure_cleans_original_guest_without_hiding_failure(assembled, cleanup_fails):
    adapter, task, session, client, tunnel, _ = assembled
    original_error = OSError(errno.EADDRINUSE, 'private-original-error')
    tunnel.start.side_effect = original_error
    with patch('backend.desktop_adapter.cleanup_prepared_guest',
               side_effect=RuntimeError('private-cleanup-error') if cleanup_fails else None) as cleanup:
        with pytest.raises(OSError) as error: adapter.prepare(task)
        assert error.value is original_error
        tunnel.close.assert_called_once()
        cleanup.assert_called_once()
        assert cleanup.call_args.kwargs['owner'] == task.owner
    root = adapter.service.settings.root / ('p2-' + task.id)
    raw = (root / 'desktop-prepare-failure.json').read_text()
    assert json.loads(raw)['cleanupConfirmed'] is (not cleanup_fails)
    assert 'private-' not in raw
    assert adapter.contexts == {}
    client.activate.assert_not_called()
    session.start.assert_not_called()


def test_disabled_cutover_rejects_before_preparation(assembled):
    adapter, task, session, client, _, gate = assembled
    adapter.settings = replace(adapter.settings, cutover_authorized=False)
    with pytest.raises(RuntimeError): adapter.prepare(task)
    adapter.command.assert_not_called()
    gate.assert_not_called()
    session.prepare.assert_not_called()


@pytest.mark.parametrize('failure', ['bootstrap', 'tunnel-close'])
def test_unknown_guest_identity_or_local_close_prevents_cleanup(assembled, failure):
    adapter, task, session, client, tunnel, _ = assembled
    if failure == 'tunnel-close':
        tunnel.start.side_effect = RuntimeError('start failure')
        tunnel.close.side_effect = RuntimeError('close unknown')
    bootstrap_patch = patch('backend.desktop_adapter.bootstrap_guest', side_effect=RuntimeError('unknown'))
    with bootstrap_patch if failure == 'bootstrap' else nullcontext(), \
            patch('backend.desktop_adapter.cleanup_prepared_guest') as cleanup:
        with pytest.raises(RuntimeError): adapter.prepare(task)
        cleanup.assert_not_called()
    root = adapter.service.settings.root / ('p2-' + task.id)
    assert json.loads((root / 'desktop-prepare-failure.json').read_text())['cleanupConfirmed'] is False
    assert adapter.cleaned_preparations == {}
    session.start.assert_not_called()


def test_prepare_settlement_requires_current_adapter_invocation(assembled):
    adapter, task, _, _, tunnel, _ = assembled
    with pytest.raises(KeyError): adapter.confirm_prepare_failure(task)
    tunnel.start.side_effect = RuntimeError('prepare failure')
    with patch('backend.desktop_adapter.cleanup_prepared_guest'):
        with pytest.raises(RuntimeError): adapter.prepare(task)
    with patch('backend.desktop_adapter.confirm_preparation_closed', return_value='proof') as confirm:
        assert adapter.confirm_prepare_failure(task) == 'proof'
        assert confirm.call_args.kwargs['task'] is task
        confirm.reset_mock()
        with pytest.raises(ValueError): adapter.confirm_prepare_failure(SimpleNamespace(**vars(task)))
        confirm.assert_not_called()


def test_failed_live_gate_prevents_app_switch_and_model_start(assembled):
    adapter, task, session, client, _, gate = assembled
    prepared = adapter.prepare(task)
    gate.return_value = False
    with pytest.raises(RuntimeError): adapter.start(prepared)
    client.activate.assert_not_called()
    session.start.assert_not_called()
    assert adapter.command.call_count == 1


def test_unverified_session_never_copies_delivery_files(assembled):
    adapter, task, _, _, _, _ = assembled
    prepared = adapter.prepare(task)
    with patch('backend.desktop_adapter.collect_guest_bundle', return_value={}), \
            patch('backend.desktop_adapter.verify_desktop_session', side_effect=ValueError('not verified')):
        with pytest.raises(ValueError): adapter.verify(prepared)
    assert list((prepared.run / 'workspace').iterdir()) == []


def test_occupied_port_refuses_before_guest_start_and_preserves_listener(assembled):
    adapter, task, session, client, tunnel, _ = assembled
    with socket.socket() as listener, patch('backend.desktop_adapter.bootstrap_guest') as bootstrap:
        listener.bind(('127.0.0.1', adapter.settings.tunnel_port))
        listener.listen()
        with pytest.raises(OSError): adapter.prepare(task)
        bootstrap.assert_not_called()
        tunnel.start.assert_not_called()
        session.start.assert_not_called()
        assert listener.getsockname()[1] == adapter.settings.tunnel_port
    path = adapter.service.settings.root / ('p2-'+task.id) / 'desktop-prepare-failure.json'
    value = json.loads(path.read_text())
    assert value['stage'] == 'tunnel-port-preflight' and value['category'] == 'OS_ERROR'
    assert not value['guestStartAttempted'] and not value['cleanupConfirmed']
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('stage', ['profile-prepare', 'guest-bootstrap', 'tunnel-start'])
def test_preparation_error_receipt_has_stage_but_no_external_error_text(assembled, stage):
    adapter, task, session, client, tunnel, _ = assembled
    secret = 'secret-token-do-not-record'
    error = OSError(errno.EADDRINUSE, secret)
    if stage == 'profile-prepare': adapter.command.side_effect = error
    elif stage == 'tunnel-start': tunnel.start.side_effect = error
    with patch('backend.desktop_adapter.bootstrap_guest', side_effect=error) if stage == 'guest-bootstrap' else nullcontext():
        with pytest.raises(OSError): adapter.prepare(task)
    path = adapter.service.settings.root / ('p2-'+task.id) / 'desktop-prepare-failure.json'
    raw = path.read_text();value = json.loads(raw)
    assert secret not in raw and value['stage'] == stage and value['errno'] == errno.EADDRINUSE
    assert value['guestNotStarted'] is False
    if stage in ('profile-prepare', 'guest-bootstrap'):
        assert adapter.cleaned_preparations == {}
    session.start.assert_not_called()
