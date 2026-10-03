import hashlib
import io
import json
import tarfile
from pathlib import Path
import sys
import pytest
from backend.desktop_bundle import decode_guest_bundle, GuestBundleUnverified
from backend.desktop_contract import DesktopSubmission

RUN = 'p2-11111111-1111-1111-1111-111111111111'
OWNER = '22222222-2222-2222-2222-222222222222'
SUBMISSION = DesktopSubmission(kind='desktop-textedit', lines=['你好'])
DOCUMENT = 'artifacts/handoff-' + RUN + '.txt'


def fixture():
    expected = SUBMISSION.expected_document()
    files = {'trace.jsonl': b'SYNTHETIC_NOT_GUI_PROOF\n', 'final_state.json': b'{}', DOCUMENT: expected,
             'result.txt': expected + b'\n', 'state-01.json': b'{}', 'state-01.png': b'\x89PNG\r\n\x1a\nTEST'}
    manifest = {'version': 1, 'binding': {'version': 1, 'runId': RUN, 'owner': OWNER, 'epoch': 1},
                'expectedSha256': hashlib.sha256(expected).hexdigest(),
                'guest': {'vmStatus': 'VERIFIED', 'runId': RUN, 'rawCalls': 10, 'sessionVerified': False,
                          'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in files.items()}}}
    return files, manifest


def pack(files, manifest, extras=()):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, data in [*files.items(), ('guest-manifest.json', json.dumps(manifest).encode()), *extras]:
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
    return buffer.getvalue()


def decode(raw):
    return decode_guest_bundle(raw, submission=SUBMISSION, run_id=RUN, owner=OWNER, epoch=1)


def test_valid_transport_envelope_does_not_claim_session_or_gui_success():
    files, manifest = fixture()
    result = decode(pack(files, manifest))
    assert result['files'] == files
    assert result['sessionVerified'] is False
    assert 'status' not in result


def test_actual_guest_archive_writer_is_compatible():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm'))
    from desktop_export import write_bundle
    files, manifest = fixture()
    output = io.BytesIO()
    write_bundle({**files, 'guest-manifest.json': json.dumps(manifest).encode()}, output)
    assert decode(output.getvalue())['files'] == files


def test_oversize_header_is_refused_without_reading_large_content():
    member = tarfile.TarInfo('trace.jsonl')
    member.size = 8 * 1024 * 1024 + 1
    with pytest.raises(GuestBundleUnverified):
        decode(member.tobuf(format=tarfile.USTAR_FORMAT) + b'\0' * 1024)


def test_pax_extension_rejected():
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT) as archive:
        member = tarfile.TarInfo('trace.jsonl')
        member.size = 1
        member.pax_headers = {'comment': 'unapproved extension'}
        archive.addfile(member, io.BytesIO(b'x'))
    with pytest.raises(GuestBundleUnverified): decode(output.getvalue())


@pytest.mark.parametrize('change', ['owner', 'epoch', 'input', 'hash', 'missing', 'document', 'session', 'boolbytes'])
def test_mismatch_rejected(change):
    files, manifest = fixture()
    if change == 'owner': manifest['binding']['owner'] = 'other'
    elif change == 'epoch': manifest['binding']['epoch'] = True
    elif change == 'input': manifest['expectedSha256'] = 'wrong'
    elif change == 'hash': files['trace.jsonl'] += b'changed'
    elif change == 'missing': del files['final_state.json']
    elif change == 'document': files[DOCUMENT] = b'wrong'
    elif change == 'session': manifest['guest']['sessionVerified'] = True
    else: manifest['guest']['files']['result.txt']['bytes'] = True
    with pytest.raises(GuestBundleUnverified): decode(pack(files, manifest))


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'control-token', 'state-31.png', 'trace.jsonl'])
def test_extra_path_or_duplicate_rejected(name):
    files, manifest = fixture()
    with pytest.raises(GuestBundleUnverified): decode(pack(files, manifest, [(name, b'bad')]))


def test_truncated_or_appended_archive_rejected():
    files, manifest = fixture()
    raw = pack(files, manifest)
    for data in (raw[:1000], raw[:-1], raw + b'x' * 512):
        with pytest.raises(GuestBundleUnverified): decode(data)


@pytest.mark.parametrize('kind', [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.DIRTYPE])
def test_nonregular_members_rejected(kind):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        member = tarfile.TarInfo('trace.jsonl')
        member.type = kind
        member.linkname = '../outside' if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ''
        archive.addfile(member)
    with pytest.raises(GuestBundleUnverified): decode(buffer.getvalue())
