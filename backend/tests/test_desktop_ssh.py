import json
import os
import subprocess
import sys

import pytest

from backend import desktop_ssh
from backend.desktop_collect import run_bounded


@pytest.fixture
def transport(tmp_path):
    # Exercise shell quoting and OpenSSH's separate option parsing.
    root = tmp_path / "transport ' $ spaced"
    root.mkdir(mode=0o700)
    hosts, askpass = root / 'known hosts', root / 'askpass'
    hosts.write_text('synthetic-host-key\n')
    hosts.chmod(0o600)
    askpass.write_text('#!/bin/sh\nexit 99\n')
    askpass.chmod(0o700)
    return dict(root=root, known_hosts=hosts, askpass=askpass)


def test_real_process_preserves_large_stdin_and_argv(transport, monkeypatch):
    fake = transport['root'] / 'fake ssh'
    fake.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
                    'print(json.dumps({"args":sys.argv[1:], "askpass":os.environ["SSH_ASKPASS"], '
                    '"force":os.environ["SSH_ASKPASS_REQUIRE"]}))\n'
                    'sys.stdout.flush()\nsys.stdout.buffer.write(sys.stdin.buffer.read())\n')
    fake.chmod(0o700)
    monkeypatch.setattr(desktop_ssh, 'SSH_BINARY', str(fake))
    wrapper = desktop_ssh.create_ssh_wrapper(**transport)
    payload = bytes(range(256)) * 4096
    output = run_bounded([str(wrapper), '-F', '/dev/null', "fixed 'remote' command"], payload,
                         limit=len(payload) + 8192, input_limit=1024 * 1024)
    header, received = output.split(b'\n', 1)
    info = json.loads(header)
    assert received == payload
    assert info['args'][-3:] == ['-F', '/dev/null', "fixed 'remote' command"]
    assert info['askpass'] == str(transport['askpass']) and info['force'] == 'force'
    assert wrapper.stat().st_mode & 0o777 == 0o700
    assert transport['known_hosts'].read_text() == 'synthetic-host-key\n'
    with pytest.raises(FileExistsError): desktop_ssh.create_ssh_wrapper(**transport)


def test_real_ssh_config_resolution_without_network(transport):
    transport['known_hosts'].chmod(0o644)
    wrapper = desktop_ssh.create_ssh_wrapper(**transport)
    result = subprocess.run([str(wrapper), '-F', '/dev/null', '-G', '-o', 'ClearAllForwardings=yes',
                             '-o', 'ForwardAgent=no', '-o', 'ControlMaster=no', 'true'],
                            capture_output=True, timeout=5, check=True, text=True)
    config = dict(line.split(' ', 1) for line in result.stdout.splitlines())
    assert config['hostname'] == '192.168.64.3' and config['user'] == 'mvpagent'
    assert config['stricthostkeychecking'] == 'true'
    assert str(transport['known_hosts']) in config['userknownhostsfile']
    assert config['stdinnull'] == 'no'
    assert config['clearallforwardings'] == 'yes' and config['forwardagent'] == 'no'


@pytest.mark.parametrize('fault', ['writable', 'link', 'not-executable'])
def test_unsafe_credentials_rejected_before_wrapper_write(transport, fault):
    if fault == 'writable':
        transport['known_hosts'].chmod(0o664)
    elif fault == 'link':
        link = transport['root'] / 'linked-hosts'
        link.symlink_to(transport['known_hosts'])
        transport['known_hosts'] = link
    else:
        transport['askpass'].chmod(0o600)
    with pytest.raises(ValueError): desktop_ssh.create_ssh_wrapper(**transport)
    assert not (transport['root'] / 'desktop-vm-ssh').exists()
