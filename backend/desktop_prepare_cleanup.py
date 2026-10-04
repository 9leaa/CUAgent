"""One cleanup attempt for the original, validated but unactivated guest."""
import json
import os
from pathlib import Path
import re
import shlex

from backend.desktop_bootstrap import validate_ready
from backend.desktop_collect import GUEST_PYTHON, private_path, run_bounded, save_exclusive


def cleanup_prepared_guest(*, root, ssh_wrapper, ready, owner, epoch):
    root = private_path(root, directory=True)
    wrapper = private_path(ssh_wrapper, directory=False)
    uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if (not os.access(wrapper, os.X_OK) or not re.fullmatch('p2-' + uuid, root.name)
            or not isinstance(owner, str) or not re.fullmatch(uuid, owner)
            or type(epoch) is not int or epoch < 1):
        raise ValueError('original cleanup binding required')
    identity = {'version': 1, 'runId': root.name, 'owner': owner, 'epoch': epoch}
    validate_ready(ready, identity)
    save_exclusive(root / 'desktop-prepare-cleanup-intent.json', json.dumps(identity).encode())
    source_root = Path(__file__).resolve().parent
    # Only reviewed local sources, never a task-provided script or remote import.
    script = ((source_root / 'desktop_client.py').read_text()
              + '\n' + (source_root / 'desktop_cleanup_protocol.py').read_text()
              + '\nraise SystemExit(cleanup_main(DesktopControlClient))\n')
    command = shlex.join([GUEST_PYTHON, '-c', script])
    args = [str(wrapper), '-F', '/dev/null', '-T', '-o', 'ClearAllForwardings=yes',
            '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no', '-o', 'ControlMaster=no', '-o', 'ControlPath=none', command]
    request = {'port': ready['controlPort'], 'token': ready['controlToken'],
               'run_id': root.name, 'owner': owner, 'epoch': epoch}
    raw = run_bounded(args, json.dumps(request).encode(), limit=4096, timeout=25)
    result = json.loads(raw)
    expected = {'binding': identity, 'closed': True, 'stopped': True,
                'active': False, 'rawCalls': 0, 'pendingCalls': 0}
    # Exact structure and types: JSON true must not count as integer 1/0.
    if (result != expected or not isinstance(result, dict)
            or any(type(result.get(k)) is not bool for k in ('closed', 'stopped', 'active'))
            or any(type(result.get(k)) is not int for k in ('rawCalls', 'pendingCalls'))
            or type(result['binding'].get('version')) is not int
            or type(result['binding'].get('epoch')) is not int):
        raise ValueError('cleanup receipt unconfirmed')
    save_exclusive(root / 'desktop-prepare-cleanup.json', json.dumps(expected).encode())
    return expected
