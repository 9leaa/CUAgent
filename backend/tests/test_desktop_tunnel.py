import errno
import secrets
import socket
import subprocess
from unittest.mock import Mock, patch
import pytest
from backend.desktop_client import DesktopControlClient, ControlUnconfirmed
from backend.desktop_tunnel import GuestControlTunnel, select_tunnel_port


def test_selection_prefers_configured_port():
    with patch('backend.desktop_tunnel.check_tunnel_port') as check:
        assert select_tunnel_port(19099) == 19099
        check.assert_called_once_with(19099)


def test_selection_skips_busy_and_wraps_only_in_control_range():
    with patch('backend.desktop_tunnel.check_tunnel_port',
               side_effect=[OSError(errno.EADDRINUSE, 'busy'), None]) as check:
        assert select_tunnel_port(19999) == 19000
        assert [c.args[0] for c in check.call_args_list] == [19999, 19000]


def test_selection_exhaustion_is_bounded_and_unique():
    with patch('backend.desktop_tunnel.check_tunnel_port',
               side_effect=OSError(errno.EADDRINUSE, 'busy')) as check:
        with pytest.raises(OSError) as error:
            select_tunnel_port(19099)
        assert error.value.errno == errno.EADDRINUSE
        assert check.call_count == 1000
        assert {c.args[0] for c in check.call_args_list} == set(range(19000, 20000))


def test_selection_does_not_hide_other_errors_or_expand_direct_port():
    for port, code in [(19099, errno.EACCES), (25000, errno.EADDRINUSE)]:
        with patch('backend.desktop_tunnel.check_tunnel_port', side_effect=OSError(code, 'failure')) as check:
            with pytest.raises(OSError) as error:
                select_tunnel_port(port)
            assert error.value.errno == code
            check.assert_called_once_with(port)


@pytest.mark.parametrize('port', [True, None, '19099', 0, 65536, 19099.0])
def test_selection_rejects_invalid_port_before_probe(port):
    with patch('backend.desktop_tunnel.check_tunnel_port') as check:
        with pytest.raises(ValueError): select_tunnel_port(port)
        check.assert_not_called()


def test_selection_preserves_real_existing_listener():
    # Find a free controlled port first; occupied ports are never taken over.
    preferred = select_tunnel_port(19000)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', preferred))
        listener.listen()
        selected = select_tunnel_port(preferred)
        assert selected != preferred and 19000 <= selected <= 19999
        assert listener.getsockname() == ('127.0.0.1', preferred)
        with socket.create_connection(('127.0.0.1', preferred), timeout=1):
            connection, _ = listener.accept()
            connection.close()


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
