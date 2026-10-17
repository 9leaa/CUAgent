"""Trusted VM-only content readback for one original Calc run; no GUI calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from calc_save import workbook_destination
from calc_workbook_verify import read_saved_workbook
from driver_smoke import require_vm


def _read_private_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or before.st_mode & 0o077
                or not 0 < before.st_size <= 16384):
            raise ValueError('private bounded binding required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(16385)
        after = os.fstat(fd)
        if (len(raw) != before.st_size
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                   (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or path.lstat() != after):
            raise ValueError('binding changed while reading')
    finally:
        os.close(fd)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('binding object required')
    return value, hashlib.sha256(raw).hexdigest()


def verify_saved_artifact(directory):
    directory = Path(directory)
    destination = workbook_destination(directory.name)
    if not directory.is_absolute() or directory.resolve(strict=True) != directory:
        raise ValueError('canonical run directory required')
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('private owned run directory required')
    filenames = ('lease.json', 'save-binding.json', 'input-binding.json')
    receipts = {name: _read_private_json(directory/name) for name in filenames}
    lease, save, inputs = (receipts[name][0] for name in filenames)
    if lease.get('runId') != directory.name or lease.get('stopped') is not True:
        raise ValueError('original revoked lease required')
    if save.get('destination') != destination:
        raise ValueError('original fixed destination required')
    if (inputs.get('cell') != 'A2' or inputs.get('approvedKind') != 'text'
            or inputs.get('inputApproved') is not True
            or inputs.get('commitApproved') is not True):
        raise ValueError('original explicit text approval required')
    result = read_saved_workbook(destination, parent_identity=save.get('parentIdentity'),
                                 sheet='Sheet1', expected_text=inputs.get('approvedText'))
    for name in filenames:
        if _read_private_json(directory/name) != receipts[name]:
            raise ValueError('original binding changed during verification')
    if directory.lstat() != info:
        raise ValueError('run directory changed during verification')
    return dict(result, runId=directory.name, destination=destination,
                bindingSha256={name: receipts[name][1] for name in filenames},
                businessStatus='UNVERIFIED')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    args = parser.parse_args(argv)
    try:
        require_vm()
        workbook_destination(args.run)
        result = verify_saved_artifact(Path.home()/'C0Evidence'/args.run)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception:
        # Never expose arbitrary workbook or credential content on rejection.
        print('CALC_ARTIFACT_UNVERIFIED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
