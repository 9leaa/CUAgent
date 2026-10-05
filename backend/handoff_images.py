"""Verify collected conversion records and actual bytes, not visual semantics.

Inputs must be read by trusted bounded collection from original private files
and official attachment storage. This function does not authenticate callers.
"""
import hashlib
import re
from backend.handoff_session import strict_json, require


def verify_handoff_images(records, observations, pngs, attachments, *, run_id, session_id, input_sha256):
    require(type(records) is list and type(observations) is list and 0 < len(records) == len(observations) <= 30)
    require(type(pngs) is dict and type(attachments) is dict)
    seen, ids, snapshots, total, checked = set(), set(), set(), 0, []
    last_used = 0
    for raw, observed in zip(records, observations):
        require(type(raw) is bytes and 0 < len(raw) <= 4096)
        record = strict_json(raw.decode('utf8'))
        require(type(record) is dict and set(record) == {'version', 'runId', 'sessionId', 'inputSha256',
            'snapshotId', 'used', 'source', 'attachment'})
        require(type(record['version']) is int and record['version'] == 1 and record['runId'] == run_id
                and record['sessionId'] == session_id and record['inputSha256'] == input_sha256)
        used, snapshot = record['used'], record['snapshotId']
        require(type(used) is int and last_used < used <= 30 and type(snapshot) is str and bool(snapshot)
                and snapshot not in snapshots and observed['snapshotId'] == snapshot
                and type(observed.get('used')) is int and observed['used'] == used)
        last_used = used; snapshots.add(snapshot)
        name = 'state-%02d.png' % used
        require(name in pngs and type(pngs[name]) is bytes and 8 <= len(pngs[name]) <= 8 * 1024 * 1024)
        source = pngs[name]; seen.add(name)
        require(source.startswith(b'\x89PNG\r\n\x1a\n') and type(record['source']) is dict
                and type(record['source'].get('bytes')) is int
                and record['source'] == {'sha256': hashlib.sha256(source).hexdigest(), 'bytes': len(source)})
        metadata = record['attachment']
        require(type(metadata) is dict and set(metadata) == {'attachmentId', 'mediaType', 'bytes', 'width', 'height'})
        key = metadata['attachmentId']
        require(type(key) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', key) and key in attachments
                and metadata['mediaType'] in ('image/png', 'image/webp')
                and all(type(metadata[k]) is int and metadata[k] > 0 for k in ('bytes', 'width', 'height')))
        original = observed['attachment']
        require(all(type(original.get(k)) is type(v) and original[k] == v for k, v in metadata.items()))
        converted = attachments[key]
        require(type(converted) is bytes and 0 < len(converted) == metadata['bytes'] <= 8 * 1024 * 1024
                and 'sha256:' + hashlib.sha256(converted).hexdigest() == key)
        if metadata['mediaType'] == 'image/png': require(converted.startswith(b'\x89PNG\r\n\x1a\n'))
        else: require(len(converted) >= 12 and converted[:4] == b'RIFF' and converted[8:12] == b'WEBP')
        total += len(raw) + len(source) + (0 if key in ids else len(converted))
        require(total <= 64 * 1024 * 1024)
        ids.add(key)
        checked.append(dict(snapshotId=snapshot, used=used, sourceSha256=record['source']['sha256'],
                            attachmentId=key, recordSha256=hashlib.sha256(raw).hexdigest()))
    require(seen == set(pngs) and ids == set(attachments))
    return {'status': 'IMAGE_PROVENANCE_VERIFIED', 'imageBytesVerified': True,
            'visualSemanticsVerified': False, 'sessionVerified': False, 'images': checked}
