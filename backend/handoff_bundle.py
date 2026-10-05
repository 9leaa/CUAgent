"""Bounded in-memory P7 transport validation; not execution acceptance."""
import hashlib
import io
import re
import tarfile
from backend.handoff_result import canonical
from backend.handoff_session import strict_json, require


def decode_handoff_bundle(raw, *, binding, materials, expected):
    require(type(raw) is bytes and 0 < len(raw) <= 65 * 1024 * 1024)
    require(type(binding) is dict and set(binding) == {'version', 'runId', 'owner', 'epoch'})
    uuid = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
    require(type(binding['version']) is int and binding['version'] == 1
            and type(binding['epoch']) is int and binding['epoch'] > 0
            and type(binding['runId']) is str and re.fullmatch('p2-' + uuid, binding['runId'])
            and type(binding['owner']) is str and re.fullmatch(uuid, binding['owner']))
    require(type(materials) is bytes and 0 < len(materials) <= 256 * 1024
            and type(expected) is bytes and 0 < len(expected) <= 4096)
    document = 'artifacts/handoff-' + binding['runId'] + '.txt'
    fixed = {'handoff-input.json', 'handoff-input-intent.json', 'handoff-input-receipt.json',
             'handoff-reopen-intent.json', 'trace.jsonl', 'final_state.json', 'result.txt', document}
    contents, total = {}, 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            for member in archive:
                name = member.name
                require(raw[member.offset + 257:member.offset + 265] == b'ustar\x0000')
                require(len(contents) < 69 and name not in contents and member.type == tarfile.REGTYPE
                        and not member.pax_headers and not member.linkname)
                require(name in fixed | {'guest-manifest.json'} or re.fullmatch(r'state-(?:0[1-9]|[12][0-9]|30)\.(?:json|png)', name))
                require(0 < member.size <= (65536 if name == 'guest-manifest.json' else 8 * 1024 * 1024))
                total += member.size
                require(total <= 64 * 1024 * 1024)
                stream = archive.extractfile(member)
                require(stream is not None)
                data = stream.read(member.size + 1)
                require(len(data) == member.size)
                contents[name] = data
            require(len(raw) % 512 == 0 and len(raw) - archive.offset >= 1024
                    and not any(raw[archive.offset:]))
        require(fixed | {'guest-manifest.json'} <= contents.keys())
        manifest = strict_json(contents.pop('guest-manifest.json').decode())
        require(type(manifest) is dict and set(manifest) == {'version', 'kind', 'binding', 'inputSha256', 'expectedSha256', 'guest'})
        require(type(manifest['version']) is int and manifest['version'] == 1 and manifest['kind'] == 'project-handoff'
                and canonical(manifest['binding']) == canonical(binding)
                and manifest['inputSha256'] == hashlib.sha256(materials).hexdigest()
                and manifest['expectedSha256'] == hashlib.sha256(expected).hexdigest())
        guest = manifest['guest']
        require(type(guest) is dict and guest.get('status') == 'VM_EVIDENCE_VERIFIED'
                and guest.get('runId') == binding['runId'] and canonical(guest.get('binding')) == canonical(binding)
                and guest.get('filesVerified') is True and guest.get('sessionVerified') is False
                and guest.get('semanticVerified') is False
                and type(guest.get('rawCalls')) is int and 1 <= guest['rawCalls'] <= 30)
        files = guest['files']
        require(type(files) is dict and files.keys() == contents.keys())
        for name, data in contents.items():
            require(canonical(files[name]) == canonical(dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))))
        require(contents['handoff-input.json'] == materials and contents[document] == expected
                and contents['result.txt'] == expected + b'\n')
        screenshots = [name for name in contents if name.endswith('.png')]
        require(bool(screenshots))
        for name in screenshots:
            require(name[:-4] + '.json' in contents and contents[name].startswith(b'\x89PNG\r\n\x1a\n'))
        for name in contents:
            if name.startswith('state-') and name.endswith('.json'): require(name[:-5] + '.png' in contents)
        return dict(status='TRANSPORT_VERIFIED', binding=dict(binding), files=contents,
                    guest=guest, sessionVerified=False, semanticVerified=False)
    except (tarfile.TarError, OSError, EOFError, UnicodeError, KeyError, TypeError, ValueError):
        raise ValueError('HANDOFF_BUNDLE_UNVERIFIED') from None
