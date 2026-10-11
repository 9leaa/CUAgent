import base64
import hashlib
import json
from pathlib import Path
import sys
import subprocess
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm'))
from desktop_install import FILES, install_package
from backend.desktop_deploy import SOURCES, build_package, deploy_guest

COMMIT = 'a' * 40


def package():
    files = {}
    for name in FILES:
        data = b'License test' if name.endswith('.md') else b'raise RuntimeError("must not execute at installation")\n'
        files[name] = {'base64': base64.b64encode(data).decode(), 'sha256': hashlib.sha256(data).hexdigest()}
    return {'commit': COMMIT, 'files': files}


def test_real_install_writes_only_new_private_sources_and_never_executes(tmp_path):
    value = package()
    reply = install_package(json.dumps(value).encode(), COMMIT, tmp_path)
    directory = Path(reply['deployment'])
    assert set(path.name for path in directory.iterdir()) == set(FILES) | {'deployment-manifest.json'}
    for path in directory.iterdir():
        assert path.stat().st_mode & 0o077 == 0
    assert hashlib.sha256((directory / 'deployment-manifest.json').read_bytes()).hexdigest() == reply['manifestSha256']
    with pytest.raises(FileExistsError): install_package(json.dumps(value).encode(), COMMIT, tmp_path)


@pytest.mark.parametrize('failure', ['hash', 'extra', 'missing', 'commit', 'syntax', 'base64'])
def test_invalid_package_rejected_before_directory_creation(tmp_path, failure):
    value = package()
    entry = value['files']['desktop_guest.py']
    if failure == 'hash': entry['sha256'] = 'bad'
    elif failure == 'extra': value['files']['../escape'] = entry
    elif failure == 'missing': del value['files']['c0_bridge.py']
    elif failure == 'commit': value['commit'] = 'b' * 40
    elif failure == 'syntax':
        data = b'if\n'
        entry.update(base64=base64.b64encode(data).decode(), sha256=hashlib.sha256(data).hexdigest())
    else: entry['base64'] = 'not valid***'
    with pytest.raises((ValueError, SyntaxError)):
        install_package(json.dumps(value).encode(), COMMIT, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_builder_reads_explicit_commit_not_working_tree(tmp_path):
    def show(args, **kwargs):
        assert args[:2] == ['git', 'show']
        assert args[2].startswith(COMMIT + ':')
        return b'# fixed source\n'
    with patch('backend.desktop_deploy.subprocess.check_output', side_effect=show) as read:
        raw, installer, digest = build_package(tmp_path, COMMIT)
    assert set(json.loads(raw)['files']) == set(FILES) == set(SOURCES) | {'LICENSE-cua.md'}
    assert {'desktop_app_cleanup.py', 'desktop_app_native.py'} <= set(SOURCES)
    assert {'handoff_input.py', 'handoff_task.py'} <= set(SOURCES)
    assert {'handoff_export.py', 'handoff_evidence.py', 'handoff_trace.py'} <= set(SOURCES)
    assert 'handoff_quote.py' in SOURCES
    assert 'handoff_draft.py' in SOURCES
    assert 'handoff_submit.py' in SOURCES
    assert {'calc_model_task.py','calc_selection.py','calc_targeting.py','calc_edit.py'} <= set(SOURCES)
    assert read.call_count == 32  # 30 Python modules, license and installer.
    assert len(digest) == 64


def test_actual_source_package_imports_without_checkout_dependencies(tmp_path):
    root=Path(__file__).resolve().parents[2]
    files={}
    for name in FILES:
        path=root/'patches/cua/LICENSE.md' if name=='LICENSE-cua.md' else root/'tools/mac_vm'/name
        data=path.read_bytes()
        files[name]=dict(base64=base64.b64encode(data).decode(),sha256=hashlib.sha256(data).hexdigest())
    result=install_package(json.dumps(dict(commit=COMMIT,files=files)).encode(),COMMIT,tmp_path)
    code='import sys;sys.path.insert(0,sys.argv[1]);import desktop_tools_http,desktop_guest,calc_model_task,calc_model_guest;assert desktop_tools_http.__file__.startswith(sys.argv[1])'
    subprocess.run([sys.executable,'-I','-c',code,result['deployment']],check=True,capture_output=True,timeout=15)


def test_deploy_single_attempt_and_strict_acknowledgement(tmp_path):
    wrapper = tmp_path / 'vm-ssh'
    wrapper.write_text('#!/bin/sh\nexit 1\n')
    wrapper.chmod(0o700)
    root = tmp_path / 'run'
    root.mkdir(mode=0o700)
    expected = {'deployment': '/Users/mvpagent/CUAgent-p6-' + COMMIT, 'manifestSha256': 'b' * 64}
    kwargs = dict(repository=tmp_path, commit=COMMIT, root=root, ssh_wrapper=wrapper)
    with patch('backend.desktop_deploy.build_package', return_value=(b'{}', '# installer', 'b' * 64)), \
            patch('backend.desktop_deploy.run_bounded', return_value=json.dumps(expected).encode()) as run:
        assert deploy_guest(**kwargs) == expected
        assert run.call_args.kwargs['input_limit'] == 1024 * 1024
        with pytest.raises(FileExistsError): deploy_guest(**kwargs)
        run.assert_called_once()


def test_vm_guard_refuses_host_before_reading_input():
    import desktop_install
    with patch.object(desktop_install.getpass, 'getuser', return_value='not-mvpagent'), \
            patch.object(desktop_install.sys, 'stdin') as stdin, patch('builtins.print'):
        assert desktop_install.main() == 1
        stdin.buffer.read.assert_not_called()
