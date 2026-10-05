import copy
import hashlib
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.handoff_attachments import read_handoff_attachments


@pytest.fixture
def evidence(tmp_path):
    home = tmp_path / 'home'; home.mkdir(mode=0o700)
    raw = b'RIFF\x04\x00\x00\x00WEBP'
    sha = hashlib.sha256(raw).hexdigest(); key = 'sha256:' + sha
    current = home
    for part in ('attachments', 'v1', 'objects', sha[:2]):
        current = current / part; current.mkdir(mode=0o700)
    path = current / sha; path.write_bytes(raw); path.chmod(0o600)
    refs = [dict(snapshotId='s', used=4, attachment=dict(attachmentId=key, mediaType='image/webp',
        bytes=len(raw), width=1, height=1, name='../../NOT_A_PATH'))]
    return home, refs, path, raw, key


def test_original_bytes_readonly_no_scan_and_repeated_digest_deduplicated(evidence):
    home, refs, path, raw, key = evidence
    refs.append(dict(refs[0], snapshotId='s2', used=7))
    with patch('os.listdir', side_effect=AssertionError('no directory scan')), patch('os.scandir', side_effect=AssertionError('no scan')):
        assert read_handoff_attachments(home, refs) == {key: raw}
    assert path.read_bytes() == raw


@pytest.mark.parametrize('fault', ['id', 'bytes', 'bool', 'format', 'used', 'snapshot', 'extra-field', 'count', 'conflicting-duplicate'])
def test_invalid_reference_refused_before_open(evidence, fault):
    home, refs, path, raw, key = evidence
    if fault == 'id': refs[0]['attachment']['attachmentId'] = '../../secret'
    elif fault == 'bytes': refs[0]['attachment']['bytes'] = 8388609
    elif fault == 'bool': refs[0]['attachment']['width'] = True
    elif fault == 'format': refs[0]['attachment']['mediaType'] = 'image/jpeg'
    elif fault == 'used': refs[0]['used'] = 31
    elif fault == 'snapshot': refs[0]['snapshotId'] = ''
    elif fault == 'extra-field': refs[0]['attachment']['path'] = '/secret'
    elif fault == 'count': refs *= 31
    else:
        other = copy.deepcopy(refs[0]); other.update(snapshotId='s2', used=7); other['attachment']['width'] = 2; refs.append(other)
    with patch('backend.handoff_attachments.os.open', side_effect=AssertionError('must reject before access')):
        with pytest.raises(ValueError): read_handoff_attachments(home, refs)


@pytest.mark.parametrize('fault', ['hash', 'length', 'public-file', 'public-directory', 'symlink', 'hardlink', 'fifo', 'missing', 'directory-link'])
def test_unsafe_or_changed_storage_denied(evidence, fault):
    home, refs, path, raw, key = evidence
    if fault == 'hash': path.write_bytes(b'x' * len(raw))
    elif fault == 'length': path.write_bytes(raw + b'x')
    elif fault == 'public-file': path.chmod(0o644)
    elif fault == 'public-directory': path.parent.chmod(0o755)
    elif fault == 'directory-link':
        original = path.parent; moved = original.with_name('original'); original.rename(moved); original.symlink_to(moved)
    else:
        path.unlink()
        if fault == 'symlink': path.symlink_to(home / 'outside')
        elif fault == 'hardlink':
            target = home / 'outside'; target.write_bytes(raw); target.chmod(0o600); os.link(target, path)
        elif fault == 'fifo': os.mkfifo(path, 0o600)
    with pytest.raises((ValueError, OSError)): read_handoff_attachments(home, refs)


def test_same_content_replaced_between_reads_is_rejected(evidence):
    home, refs, path, raw, key = evidence; original_open = os.open; reads = 0
    def changing_open(name, *args, **kwargs):
        nonlocal reads
        if name == key[7:]:
            reads += 1
            if reads == 2:
                path.rename(path.with_name('original'))
                path.write_bytes(raw); path.chmod(0o600)
        return original_open(name, *args, **kwargs)
    with patch('backend.handoff_attachments.os.open', side_effect=changing_open):
        with pytest.raises(ValueError): read_handoff_attachments(home, refs)


def test_total_byte_limit_checked_before_access(evidence):
    home, refs, *_ = evidence
    refs = [dict(snapshotId=str(i), used=i+1, attachment=dict(refs[0]['attachment'],
        attachmentId='sha256:'+f'{i:064x}', bytes=8*1024*1024)) for i in range(9)]
    with patch('backend.handoff_attachments.os.open', side_effect=AssertionError('must reject before access')):
        with pytest.raises(ValueError): read_handoff_attachments(home, refs)
