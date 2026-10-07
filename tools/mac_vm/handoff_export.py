"""VM-only frozen P7 evidence export; no model or GUI actions."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from desktop_control import LeaseController
from desktop_export import write_bundle
from desktop_guest import UUID
from driver_smoke import require_vm
from handoff_evidence import inspect_handoff_evidence, strict_json, require


def input_from_stream(stream):
    raw = stream.read(512 * 1024 + 1)
    require(len(raw) <= 512 * 1024)
    value = strict_json(raw)
    require(type(value) is dict and set(value) == {'materialsBase64', 'expectedBase64'})
    materials, expected = (base64.b64decode(value[key], validate=True)
                           for key in ('materialsBase64', 'expectedBase64'))
    require(0 < len(materials) <= 256 * 1024 and 0 < len(expected) <= 4096)
    return materials, expected


def build_bundle(directory, controller, materials, expected):
    root = Path(directory).absolute()
    require(controller.path == root / 'lease.json' and controller.gate.run_id == root.name)
    lease = controller.existing()
    require(lease is not None and lease['stopped'] is True)
    binding = {key: lease[key] for key in ('version', 'runId', 'owner', 'epoch')}
    report = inspect_handoff_evidence(root, binding=binding, materials=materials, expected=expected)
    fixed = {'handoff-input.json', 'handoff-input-intent.json', 'handoff-input-receipt.json',
             'handoff-reopen-intent.json', 'trace.jsonl', 'final_state.json', 'result.txt',
             'artifacts/handoff-' + root.name + '.txt'}
    if 'handoff-session-binding.json' in report['files']:
        fixed.add('handoff-session-binding.json')
    contents, signatures = {}, {}
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_nlink)
    root_signature = signature(root.stat())
    def read(name):
        require(name in fixed or re.fullmatch(r'state-(?:0[1-9]|[12][0-9]|30)\.(?:json|png)', name))
        path = root / name
        require(path.resolve(strict=True) == path)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                    and 0 < info.st_size <= 8 * 1024 * 1024)
            data = stream.read(info.st_size + 1)
            require(len(data) == info.st_size and signature(os.fstat(stream.fileno())) == signature(info))
        require(signature(path.stat(follow_symlinks=False)) == signature(info))
        require(report['files'][name] == {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        if name in signatures: require(signatures[name] == signature(info) and contents[name] == data)
        else: signatures[name] = signature(info)
        return data
    total = 0
    for name in report['files']:
        data = read(name)
        total += len(data)
        require(total <= 64 * 1024 * 1024)
        contents[name] = data
    require(fixed <= contents.keys())
    for name in contents: read(name)
    require(root.resolve(strict=True) == root and signature(root.stat()) == root_signature)
    require(controller.existing() == lease)
    manifest = dict(version=1, kind='project-handoff', binding=binding,
        inputSha256=hashlib.sha256(materials).hexdigest(), expectedSha256=hashlib.sha256(expected).hexdigest(), guest=report)
    contents['guest-manifest.json'] = json.dumps(manifest, sort_keys=True).encode()
    return contents


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--epoch', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        require_vm()
        require(re.fullmatch('p2-' + UUID, args.run) and re.fullmatch(UUID, args.owner) and args.epoch > 0)
        root = Path.home() / 'C0Evidence' / args.run
        controller = LeaseController(root / 'lease.json', run_id=args.run, owner=args.owner,
                                     epoch=args.epoch, clock=time.time)
        contents = build_bundle(root, controller, *input_from_stream(sys.stdin.buffer))
        write_bundle(contents, sys.stdout.buffer)
        return 0
    except Exception:
        print('P7_GUEST_EXPORT_UNVERIFIED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
