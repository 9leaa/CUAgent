"""Validate trusted-channel guest exports in memory; never extract or mark success."""
import hashlib
import io
import json
import re
import tarfile

from backend.desktop_contract import DesktopSubmission


class GuestBundleUnverified(ValueError):
    pass


def require(condition):
    if not condition:
        raise GuestBundleUnverified('GUEST_BUNDLE_UNVERIFIED')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def decode_guest_bundle(raw, *, submission, run_id, owner, epoch):
    """Caller owns SSH provenance; a self-consistent arbitrary tar is not proof."""
    require(isinstance(raw, bytes) and 0 < len(raw) <= 65 * 1024 * 1024)
    require(isinstance(submission, DesktopSubmission))
    uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    require(isinstance(run_id, str) and re.fullmatch('p2-' + uuid, run_id))
    require(isinstance(owner, str) and re.fullmatch(uuid, owner) and type(epoch) is int and epoch > 0)
    document = 'artifacts/handoff-' + run_id + '.txt'
    fixed = {'trace.jsonl', 'final_state.json', 'result.txt', document, 'guest-manifest.json'}
    contents = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            for member in archive:
                name = member.name
                require(len(contents) < 65 and name not in contents and member.type == tarfile.REGTYPE
                        and not member.pax_headers and not member.linkname)
                require(name in fixed or re.fullmatch(r'state-(?:0[1-9]|[12][0-9]|30)\.(?:json|png)', name))
                require(0 < member.size <= (65536 if name == 'guest-manifest.json' else 8 * 1024 * 1024))
                total += member.size
                require(total <= 64 * 1024 * 1024)
                stream = archive.extractfile(member)
                require(stream is not None)
                data = stream.read(member.size + 1)
                require(len(data) == member.size)
                contents[name] = data
            # Exporter emits a complete, zero-padded archive. Do not accept
            # truncated end blocks or trailing second archives/hidden data.
            require(len(raw) % 512 == 0 and len(raw) - archive.offset >= 1024)
            require(not any(raw[archive.offset:]))
        require(fixed <= contents.keys())
        manifest = json.loads(contents.pop('guest-manifest.json'), object_pairs_hook=unique_object)
        require(isinstance(manifest, dict) and set(manifest) == {'version', 'binding', 'expectedSha256', 'guest'})
        require(type(manifest['version']) is int and manifest['version'] == 1)
        binding = manifest['binding']
        require(isinstance(binding, dict) and binding == {'version': 1, 'runId': run_id, 'owner': owner, 'epoch': epoch})
        require(type(binding['version']) is int and type(binding['epoch']) is int)
        expected = submission.expected_document()
        require(manifest['expectedSha256'] == hashlib.sha256(expected).hexdigest())
        guest = manifest['guest']
        require(isinstance(guest, dict) and guest.get('vmStatus') == 'VERIFIED'
                and guest.get('runId') == run_id and guest.get('sessionVerified') is False
                and type(guest.get('rawCalls')) is int and 1 <= guest['rawCalls'] <= 30)
        files = guest.get('files')
        require(isinstance(files, dict) and files.keys() == contents.keys())
        for name, data in contents.items():
            metadata = files[name]
            require(isinstance(metadata, dict) and type(metadata.get('bytes')) is int
                    and metadata == {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        require(contents[document] == expected and contents['result.txt'] == expected + b'\n')
        screenshots = [name for name in contents if name.endswith('.png')]
        require(bool(screenshots))
        for name in screenshots:
            require(name[:-4] + '.json' in contents and contents[name].startswith(b'\x89PNG\r\n\x1a\n'))
        for name in contents:
            if name.startswith('state-') and name.endswith('.json'):
                require(name[:-5] + '.png' in contents)
        return {'binding': binding, 'files': contents, 'guest': guest, 'sessionVerified': False}
    except (tarfile.TarError, OSError, EOFError, UnicodeError, KeyError, TypeError, ValueError):
        raise GuestBundleUnverified('GUEST_BUNDLE_UNVERIFIED') from None
