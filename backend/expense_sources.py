"""Bounded read-only collection of trusted expense source bytes, not document decoding."""
import hashlib
import os
from pathlib import Path
import stat

from .expense_contract import ExpenseSubmission

EXTENSIONS = {'application/pdf': '.pdf', 'image/png': '.png', 'image/jpeg': '.jpeg'}


def _require(condition):
    if not condition:
        raise ValueError('EXPENSE_SOURCE_COLLECTION_UNVERIFIED')


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_mode, info.st_uid, info.st_nlink)


def _read_source(root_fd, receipt):
    filename = receipt.id + EXTENSIONS[receipt.mediaType]
    fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        _require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                 and not before.st_mode & 0o077 and before.st_nlink == 1
                 and before.st_size == receipt.sizeBytes)
        raw = stream.read(receipt.sizeBytes + 1)
        after = os.fstat(stream.fileno())
    _require(_signature(before) == _signature(after)
             == _signature(os.stat(filename, dir_fd=root_fd, follow_symlinks=False)))
    _require(len(raw) == receipt.sizeBytes and hashlib.sha256(raw).hexdigest() == receipt.sha256)
    return raw, _signature(after)


def collect_expense_sources(root, submission):
    """Caller owns/freeze-locks root; input manifest is independent of any model report."""
    submission = ExpenseSubmission.model_validate(submission)
    root = Path(root)
    _require(root.is_absolute())
    fd = None
    try:
        _require(root.resolve(strict=True) == root)
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        initial = os.fstat(fd)
        _require(initial.st_uid == os.getuid() and not initial.st_mode & 0o077)
        collected = {receipt.id: _read_source(fd, receipt) for receipt in submission.receipts}
        for receipt in submission.receipts:
            _require(_read_source(fd, receipt) == collected[receipt.id])
        _require(root.resolve(strict=True) == root
                 and _signature(initial) == _signature(os.fstat(fd))
                 == _signature(root.stat(follow_symlinks=False)))
        return dict(status='SOURCE_BYTES_VERIFIED', inputSha256=submission.input_sha256(),
                    decodedFormatVerified=False, extractionVerified=False, guiVerified=False,
                    files={source_id: raw for source_id, (raw, _) in collected.items()})
    except (OSError, RuntimeError, ValueError):
        raise ValueError('EXPENSE_SOURCE_COLLECTION_UNVERIFIED') from None
    finally:
        if fd is not None:
            os.close(fd)
