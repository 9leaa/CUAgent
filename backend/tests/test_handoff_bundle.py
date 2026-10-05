import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import pytest
from backend.handoff_bundle import decode_handoff_bundle

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm/tests'))
import test_handoff_evidence
from desktop_control import LeaseController
from desktop_export import write_bundle
from handoff_export import build_bundle


@pytest.fixture
def bundle():
    f = test_handoff_evidence.HandoffEvidenceTests(); f.setUp()
    try:
        f.binding['owner'] = '11111111-1111-1111-1111-111111111111'
        for name in ('handoff-input-intent.json', 'handoff-input-receipt.json'):
            path = f.root / name; value = json.loads(path.read_bytes()); value['binding'] = f.binding
            path.write_text(json.dumps(value))
        controller = LeaseController(f.root / 'lease.json', run_id=f.root.name,
            owner=f.binding['owner'], epoch=1, clock=lambda: 100)
        controller.revoke()
        args = dict(binding=f.binding, materials=f.fixture.materials, expected=f.fixture.expected)
        yield build_bundle(f.root, controller, args['materials'], args['expected']), args
    finally: f.doCleanups()


def archive(contents):
    out = io.BytesIO(); write_bundle(contents, out); return out.getvalue()


def test_real_export_decoded_in_memory_not_business_acceptance(bundle):
    contents, args = bundle
    original = copy.deepcopy(contents)
    result = decode_handoff_bundle(archive(contents), **args)
    assert result['status'] == 'TRANSPORT_VERIFIED'
    assert result['sessionVerified'] is result['semanticVerified'] is False
    assert result['files'] == {k: v for k, v in contents.items() if k != 'guest-manifest.json'}
    assert contents == original


@pytest.mark.parametrize('fault', ['missing', 'bytes', 'path', 'token', 'kind', 'epoch', 'input', 'document', 'numeric', 'pair', 'semantic'])
def test_tampered_bundle_refused(bundle, fault):
    contents, args = bundle
    manifest = json.loads(contents['guest-manifest.json'])
    if fault == 'missing': del contents['trace.jsonl']
    elif fault == 'bytes': contents['trace.jsonl'] += b'x'
    elif fault == 'path': contents['../escape'] = b'x'
    elif fault == 'token': contents['control-token'] = b'x'
    elif fault == 'kind': manifest['kind'] = 'desktop-textedit'
    elif fault == 'epoch': manifest['binding']['epoch'] = True
    elif fault == 'input': manifest['inputSha256'] = '0'*64
    elif fault == 'document':
        contents['result.txt'] = b'wrong'
        manifest['guest']['files']['result.txt'] = dict(bytes=5, sha256=hashlib.sha256(b'wrong').hexdigest())
    elif fault == 'numeric': manifest['guest']['rawCalls'] = True
    elif fault == 'semantic': manifest['guest']['semanticVerified'] = True
    else:
        name = next(k for k in contents if k.endswith('.png'))
        del contents[name]; del manifest['guest']['files'][name]
    contents['guest-manifest.json'] = json.dumps(manifest).encode()
    with pytest.raises(ValueError): decode_handoff_bundle(archive(contents), **args)


@pytest.mark.parametrize('fault', ['duplicate', 'link', 'directory', 'pax', 'gnu', 'trailing', 'truncated'])
def test_archive_structure_refused(bundle, fault):
    contents, args = bundle
    if fault in ('trailing', 'truncated'):
        raw = archive(contents)
        raw = raw + b'hidden' if fault == 'trailing' else raw[:512]
    else:
        output = io.BytesIO()
        format = {'pax': tarfile.PAX_FORMAT, 'gnu': tarfile.GNU_FORMAT}.get(fault, tarfile.USTAR_FORMAT)
        with tarfile.open(fileobj=output, mode='w', format=format) as tar:
            for name, data in contents.items():
                item = tarfile.TarInfo(name); item.size = len(data)
                if name == 'trace.jsonl':
                    if fault == 'link': item.type = tarfile.SYMTYPE; item.linkname = '/tmp/secret'; item.size = 0
                    if fault == 'directory': item.type = tarfile.DIRTYPE; item.size = 0
                    if fault == 'pax': item.pax_headers = {'comment': 'hidden'}
                tar.addfile(item, io.BytesIO(data))
                if fault == 'duplicate' and name == 'trace.jsonl': tar.addfile(item, io.BytesIO(data))
        raw = output.getvalue()
    with pytest.raises(ValueError): decode_handoff_bundle(raw, **args)
