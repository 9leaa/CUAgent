import copy
import hashlib
import json
import pytest
from backend.handoff_images import verify_handoff_images


def fixture():
    png = b'\x89PNG\r\n\x1a\nSIMULATED_SOURCE_NOT_VISUAL_PROOF'
    webp = b'RIFF\x04\x00\x00\x00WEBP'
    key = 'sha256:' + hashlib.sha256(webp).hexdigest()
    attachment = dict(attachmentId=key, mediaType='image/webp', bytes=len(webp), width=1, height=1)
    record = dict(version=1, runId='run', sessionId='session', inputSha256='a'*64, snapshotId='s', used=4,
                  source=dict(sha256=hashlib.sha256(png).hexdigest(), bytes=len(png)), attachment=attachment)
    return record, [dict(snapshotId='s', used=4, attachment=copy.deepcopy(attachment))], {'state-04.png': png}, {key: webp}


def verify(record, observations, pngs, attachments):
    return verify_handoff_images([json.dumps(record).encode()], observations, pngs, attachments,
                                run_id='run', session_id='session', input_sha256='a'*64)


def test_exact_conversion_chain_checks_actual_bytes_not_visual_claim():
    data = fixture(); before = copy.deepcopy(data)
    result = verify(*data)
    assert result['imageBytesVerified'] is True
    assert result['visualSemanticsVerified'] is result['sessionVerified'] is False
    assert data == before


@pytest.mark.parametrize('fault', ['run', 'session', 'input', 'used', 'bool', 'snapshot', 'source', 'source-bytes',
    'source-hash', 'output', 'output-size', 'output-hash', 'missing', 'extra', 'metadata', 'format', 'empty'])
def test_broken_chain_refused(fault):
    record, observations, pngs, attachments = fixture(); key = next(iter(attachments))
    if fault == 'run': record['runId'] = 'other'
    elif fault == 'session': record['sessionId'] = 'other'
    elif fault == 'input': record['inputSha256'] = '0'*64
    elif fault == 'used': record['used'] = 31
    elif fault == 'bool': record['version'] = True
    elif fault == 'snapshot': record['snapshotId'] = 'other'
    elif fault == 'source': pngs['state-04.png'] += b'x'
    elif fault == 'source-bytes': record['source']['bytes'] = True
    elif fault == 'source-hash': record['source']['sha256'] = '0'*64
    elif fault == 'output': attachments[key] += b'x'
    elif fault == 'output-size': record['attachment']['bytes'] = True
    elif fault == 'output-hash': record['attachment']['attachmentId'] = 'sha256:'+'0'*64
    elif fault == 'missing': attachments.clear()
    elif fault == 'extra': pngs['other.png'] = b'x'
    elif fault == 'metadata': observations[0]['attachment']['width'] = 2
    elif fault == 'format': record['attachment']['mediaType'] = 'image/jpeg'
    else: observations.clear()
    with pytest.raises(ValueError): verify(record, observations, pngs, attachments)
