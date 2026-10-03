from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from backend.desktop_adapter import DesktopAdapterSettings, DesktopTaskAdapter


@pytest.fixture
def assembled(tmp_path):
    service = Mock()
    service.settings.root = tmp_path
    task = SimpleNamespace(id='11111111-1111-1111-1111-111111111111', owner='22222222-2222-2222-2222-222222222222',
                           epoch=1, payload={'kind': 'desktop-textedit', 'lines': ['synthetic']})
    settings = DesktopAdapterSettings(node=tmp_path / 'node', official_home=tmp_path / 'home', cookie=tmp_path / 'cookie',
        build_tools=tmp_path / 'tools', base_tasks=tmp_path / 'tasks', ssh_wrapper=tmp_path / 'ssh',
        guest_commit='a' * 40, guest_manifest_sha='b' * 64, tunnel_port=19001, cutover_authorized=True)
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
                        'result.txt': b'synthetic\n\n'}, 'guest': {'rawCalls': 12}}
    with patch('backend.desktop_adapter.collect_guest_bundle', return_value=bundle), \
            patch('backend.desktop_adapter.verify_desktop_session', return_value={'sessionVerified': True}):
        result = adapter.verify(prepared)
    assert result['status'] == 'SUCCEEDED'
    assert (prepared.run / 'workspace/document.txt').read_bytes() == b'synthetic\n'
    adapter.restore(prepared)
    client.shutdown.assert_called_once()
    tunnel.close.assert_called_once()
    assert [call.args[2] for call in adapter.command.call_args_list][-3:] == ['stop-restore', 'restore', 'start-restore']


def test_disabled_cutover_rejects_before_preparation(assembled):
    adapter, task, session, client, _, gate = assembled
    adapter.settings = replace(adapter.settings, cutover_authorized=False)
    with pytest.raises(RuntimeError): adapter.prepare(task)
    adapter.command.assert_not_called()
    gate.assert_not_called()
    session.prepare.assert_not_called()


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
