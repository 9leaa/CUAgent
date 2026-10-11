"""Deploy only reviewed sources from an explicit commit; no service activation."""
import base64
import hashlib
import json
import os
import re
import shlex
import subprocess

from backend.desktop_collect import GUEST_PYTHON, private_path, run_bounded, save_exclusive

SOURCES = ('desktop_guest.py', 'desktop_export.py', 'desktop_runtime.py', 'desktop_control.py',
           'calc_model_task.py', 'calc_model_guest.py', 'calc_runtime.py', 'calc_selection.py', 'calc_targeting.py',
           'desktop_app_cleanup.py', 'desktop_app_native.py', 'handoff_input.py', 'handoff_task.py',
           'handoff_export.py', 'handoff_evidence.py', 'handoff_trace.py', 'handoff_quote.py', 'handoff_draft.py', 'handoff_submit.py',
           'desktop_control_http.py', 'desktop_lease.py', 'desktop_tools_http.py', 'desktop_evidence.py',
           'real_app_bridge.py', 'real_app_verifier.py', 'c0_bridge.py', 'c0_cases.py', 'c0_identity.py',
           'driver_smoke.py')


def build_package(repository, commit):
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('explicit full commit required')
    def source(path):
        return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=repository,
                                       stderr=subprocess.DEVNULL, timeout=10)
    files = {}
    for name in (*SOURCES, 'LICENSE-cua.md'):
        path = 'patches/cua/LICENSE.md' if name == 'LICENSE-cua.md' else 'tools/mac_vm/' + name
        data = source(path)
        if not 0 < len(data) <= 256 * 1024:
            raise ValueError('source size exceeded')
        files[name] = {'base64': base64.b64encode(data).decode(), 'sha256': hashlib.sha256(data).hexdigest()}
    package = json.dumps({'commit': commit, 'files': files}, sort_keys=True).encode()
    if len(package) > 1024 * 1024:
        raise ValueError('package too large')
    installer = source('tools/mac_vm/desktop_install.py').decode('utf8')
    if len(installer.encode()) > 32768:
        raise ValueError('installer too large')
    manifest = json.dumps({'commit': commit, 'files': {key: value['sha256'] for key, value in files.items()}}, sort_keys=True).encode()
    return package, installer, hashlib.sha256(manifest).hexdigest()


def deploy_guest(*, repository, commit, root, ssh_wrapper):
    root = private_path(root, directory=True)
    wrapper = private_path(ssh_wrapper, directory=False)
    if not os.access(wrapper, os.X_OK):
        raise ValueError('trusted executable wrapper required')
    package, installer, digest = build_package(repository, commit)
    expected = {'deployment': '/Users/mvpagent/CUAgent-p6-' + commit, 'manifestSha256': digest}
    save_exclusive(root / 'desktop-deployment-intent.json', json.dumps(expected).encode())
    command = shlex.join([GUEST_PYTHON, '-c', installer, commit])
    args = [str(wrapper), '-F', '/dev/null', '-T', '-o', 'ClearAllForwardings=yes',
            '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no', '-o', 'ControlMaster=no', '-o', 'ControlPath=none', command]
    raw = run_bounded(args, package, limit=4096, timeout=45, input_limit=1024 * 1024)
    save_exclusive(root / 'desktop-deployment-response.json', raw)
    if json.loads(raw) != expected:
        raise ValueError('deployment acknowledgement mismatch')
    return expected
