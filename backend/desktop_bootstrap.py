"""Single-attempt guest launch. Receipt contains per-run secrets: never log it."""
import json
import os
from pathlib import Path
import re
import shlex

from backend.desktop_collect import GUEST_PYTHON, private_path, run_bounded, save_exclusive


def bootstrap_guest(*, root, ssh_wrapper, commit, manifest_sha, owner, epoch):
    root = private_path(root, directory=True)
    wrapper = private_path(ssh_wrapper, directory=False)
    uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if (not os.access(wrapper, os.X_OK) or not re.fullmatch('p2-' + uuid, root.name)
            or not re.fullmatch(uuid, owner) or type(epoch) is not int or epoch < 1
            or not re.fullmatch(r'[0-9a-f]{40}', commit) or not re.fullmatch(r'[0-9a-f]{64}', manifest_sha)):
        raise ValueError('fixed guest bootstrap identity required')
    identity = {'version': 1, 'runId': root.name, 'owner': owner, 'epoch': epoch}
    save_exclusive(root / 'desktop-guest-start-intent.json', json.dumps({'binding': identity, 'commit': commit,
                                                                      'manifestSha256': manifest_sha}).encode())
    script = (Path(__file__).resolve().parents[1] / 'tools/mac_vm/desktop_bootstrap.py').read_text()
    command = shlex.join([GUEST_PYTHON, '-c', script, commit, manifest_sha, root.name, owner, str(epoch)])
    args = [str(wrapper), '-F', '/dev/null', '-T', '-o', 'ClearAllForwardings=yes',
            '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no', '-o', 'ControlMaster=no', '-o', 'ControlPath=none', command]
    raw = run_bounded(args, b'', limit=4096, timeout=25)
    save_exclusive(root / 'guest-private-receipt.json', raw)
    ready = json.loads(raw)
    if (not isinstance(ready, dict) or ready.get('binding') != identity
            or type(ready['binding'].get('version')) is not int or type(ready['binding'].get('epoch')) is not int
            or ready.get('activated') is not False or ready.get('controlHost') != '127.0.0.1'
            or ready.get('modelUrl') != 'http://192.168.64.3:8766'
            or type(ready.get('controlPort')) is not int or not 1 <= ready['controlPort'] <= 65535
            or type(ready.get('pid')) is not int or ready['pid'] <= 1
            or any(not isinstance(ready.get(key), str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', ready[key])
                   for key in ('modelToken', 'controlToken')) or ready['modelToken'] == ready['controlToken']):
        raise ValueError('guest bootstrap receipt unconfirmed')
    return ready
