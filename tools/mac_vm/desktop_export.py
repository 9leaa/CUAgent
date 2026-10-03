"""VM-only read-only evidence export. Never exports credentials or grants a lease."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import time
import unicodedata

from desktop_control import LeaseController
from desktop_evidence import inspect_guest_evidence
from desktop_guest import UUID
from driver_smoke import require_vm


def expected_from_stream(stream):
    raw = stream.read(32769)
    if len(raw) > 32768:
        raise ValueError('input limit')
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {'lines'}:
        raise ValueError('lines required')
    lines = value['lines']
    if (not isinstance(lines, list) or not 1 <= len(lines) <= 10
            or any(not isinstance(line, str) or not line.strip()
                   or any(unicodedata.category(char) in {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'} for char in line)
                   for line in lines)):
        raise ValueError('invalid lines')
    expected = ('\n'.join(lines) + '\n').encode('utf8')
    if len(expected) > 4096:
        raise ValueError('document limit')
    return expected


def build_bundle(directory, controller, expected):
    root = Path(directory).absolute()
    if controller.path != root / 'lease.json' or controller.gate.run_id != root.name:
        raise ValueError('fixed controller path required')
    lease = controller.existing()
    if lease is None or lease['stopped'] is not True:
        raise ValueError('revoked lease required')
    report = inspect_guest_evidence(root, run_id=root.name, expected=expected)
    contents = {}
    total = 0
    document = 'artifacts/handoff-' + root.name + '.txt'
    for name, metadata in report['files'].items():
        if name not in {'trace.jsonl', 'final_state.json', 'result.txt', document} and not re.fullmatch(r'state-(?:0[1-9]|[12][0-9]|30)\.(?:json|png)', name):
            raise ValueError('export path not allowed')
        path = root / name
        if path.resolve(strict=True) != path:
            raise ValueError('export link refused')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 8 * 1024 * 1024:
                raise ValueError('invalid export file')
            data = stream.read(8 * 1024 * 1024 + 1)
        if {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} != metadata:
            raise ValueError('evidence changed before export')
        total += len(data)
        if total > 64 * 1024 * 1024:
            raise ValueError('export total limit')
        contents[name] = data
    if controller.existing() != lease:
        raise ValueError('lease changed during export')
    # Manifest is collection metadata, not model/session acceptance.
    manifest = {'version': 1, 'binding': {key: lease[key] for key in ('version', 'runId', 'owner', 'epoch')},
                'expectedSha256': hashlib.sha256(expected).hexdigest(), 'guest': report}
    contents['guest-manifest.json'] = (json.dumps(manifest, sort_keys=True) + '\n').encode()
    return contents


def write_bundle(contents, output):
    # All checks and source reads finish before the first archive byte is sent.
    with tarfile.open(fileobj=output, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(contents.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o600, 0
            archive.addfile(info, io.BytesIO(data))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--epoch', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        require_vm()
        if not re.fullmatch('p2-' + UUID, args.run) or not re.fullmatch(UUID, args.owner) or args.epoch < 1:
            raise ValueError('invalid binding')
        directory = Path.home() / 'C0Evidence' / args.run
        controller = LeaseController(directory / 'lease.json', run_id=args.run, owner=args.owner,
                                     epoch=args.epoch, clock=time.time)
        contents = build_bundle(directory, controller, expected_from_stream(sys.stdin.buffer))
        write_bundle(contents, sys.stdout.buffer)
        return 0
    except Exception:
        print('P6_GUEST_EXPORT_UNVERIFIED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
