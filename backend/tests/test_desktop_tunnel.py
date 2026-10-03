import secrets
import socket
import subprocess
from unittest.mock import Mock, patch
import pytest
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed
from backend.desktop_tunnel import GuestControlTunnel


@pytest.fixture
def tunnel(tmp_path):
    wrapper = tmp_path / 'vm-ssh'
    wrapper.write_text('#!/bin/sh\nexit 1\n')
    wrapper.chmod(0o700)
    run = tmp_path / 'task'
    run.mkdir(mode=0o700)
    with socket.socket() as port:
        port.bind(('127.0.0.1', 0))
        number = port.getsockname()[1]
    client = DesktopControlClient(port=number, token=secrets.token_urlsafe(32), run_id='task', owner='owner', epoch=1)
    client.inspect = Mock(return_value={'binding': client.identity, 'lease': None})
    return GuestControlTunnel(root=run, ssh_wrapper=wrapper, guest_port=19001, client=client)


def test_single_owned_process_fixed_forward_and_no_secrets(tunnel):
    process = Mock()
    process.poll.return_value = None
    with patch('backend.desktop_tunnel.subprocess.Popen', return_value=process) as popen:
        assert tunnel.start()['binding'] == tunnel.client.identity
        args = popen.call_args.args[0]
        assert args[-2:] == ['-L', f'127.0.0.1:{tunnel.client.port}:127.0.0.1:19001']
        assert '-N' in args and 'ExitOnForwardFailure=yes' in args and 'ControlPath=none' in args
        assert args[1:3] == ['-F', '/dev/null']
        assert tunnel.client.token not in str(popen.call_args)
        assert tunnel.client.token not in (tunnel.root / 'desktop-tunnel-intent.json').read_text()
        with pytest.raises(ControlUnconfirmed):
            tunnel.start()
        popen.assert_called_once()
        tunnel.close()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=2)


def test_existing_listener_not_touched(tunnel):
    with socket.socket() as listener, patch('backend.desktop_tunnel.subprocess.Popen') as popen:
        listener.bind(('127.0.0.1', tunnel.client.port))
        listener.listen()
        with pytest.raises(OSError):
            tunnel.start()
        popen.assert_not_called()
        assert listener.getsockname()[1] == tunnel.client.port


def test_wrong_identity_stops_owned_process_without_retry(tunnel):
    tunnel.client.inspect.side_effect = ControlUnconfirmed('GUEST_CONTROL_BINDING_MISMATCH')
    process = Mock()
    process.poll.return_value = None
    with patch('backend.desktop_tunnel.subprocess.Popen', return_value=process) as popen:
        with pytest.raises(ControlUnconfirmed):
            tunnel.start()
        popen.assert_called_once()
        process.terminate.assert_called_once()
        tunnel.client.inspect.assert_called_once()


def test_start_failure_persists_intent_across_objects(tunnel):
    with patch('backend.desktop_tunnel.subprocess.Popen', side_effect=OSError('failed')) as popen:
        with pytest.raises(OSError):
            tunnel.start()
        replacement = GuestControlTunnel(root=tunnel.root, ssh_wrapper=tunnel.wrapper,
                                         guest_port=tunnel.guest_port, client=tunnel.client)
        with pytest.raises(FileExistsError):
            replacement.start()
        popen.assert_called_once()


def test_start_timeout_and_force_close_are_bounded(tunnel):
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired('ssh', 2), 0]
    with patch('backend.desktop_tunnel.subprocess.Popen', return_value=process), \
            patch('backend.desktop_tunnel.time.monotonic', side_effect=[0, 11]):
        with pytest.raises(ControlUnconfirmed, match='TIMEOUT'):
            tunnel.start()
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert process.wait.call_count == 2


def test_insecure_or_linked_wrapper_refused(tunnel):
    tunnel.wrapper.chmod(0o755)
    with pytest.raises(ValueError):
        GuestControlTunnel(root=tunnel.root, ssh_wrapper=tunnel.wrapper, guest_port=19001, client=tunnel.client)
    tunnel.wrapper.chmod(0o700)
    link = tunnel.wrapper.with_name('linked-ssh')
    link.symlink_to(tunnel.wrapper)
    with pytest.raises(ValueError):
        GuestControlTunnel(root=tunnel.root, ssh_wrapper=link, guest_port=19001, client=tunnel.client)
