import json

import pytest
from backend.handoff_result import canonical
from backend.handoff_verify import verify_handoff_execution
from backend.tests.test_handoff_verify import evidence


@pytest.mark.parametrize('evidence', ['with_submit'], indirect=True)
def test_full_combined_submission_chain_original_producer_and_subprocess(evidence):
    kwargs, _, _ = evidence
    result = verify_handoff_execution(**kwargs, protocol='p7-tool-submit-v1')
    assert result['status'] == 'EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING'
    assert result['protocol'] == 'p7-tool-submit-v1'
    assert result['submissionEvidence']['status'] == 'SUBMISSION_EVIDENCE_MATCHED'
    assert result['submissionEvidence']['rawCalls'] == 18
    assert result['sessionVerified'] and result['guiEvidenceVerified'] and result['imageBytesVerified']
    assert not result['semanticVerified']


@pytest.mark.parametrize('evidence', ['with_submit'], indirect=True)
@pytest.mark.parametrize('fault', ['legacy', 'missing_intent', 'changed_intent', 'public_intent',
    'missing_protocol', 'changed_binding', 'audit_old_tools', 'guest_wrong_session'])
def test_original_protocol_intent_cannot_be_missing_changed_or_inferred(evidence, fault):
    kwargs, _, audit = evidence
    root = kwargs['root']
    if fault == 'missing_intent': (root / 'desktop-request.json').unlink()
    if fault == 'public_intent': (root / 'desktop-request.json').chmod(0o644)
    if fault in ('changed_intent', 'missing_protocol', 'changed_binding'):
        path = root / ('desktop-request.json' if fault == 'changed_intent' else 'desktop-session-binding.json')
        data = json.loads(path.read_bytes())
        if fault == 'missing_protocol': del data['protocol']
        elif fault == 'changed_intent': data['inputSha256'] = '0' * 64
        else: data['protocol'] = 'legacy-final-json'
        path.write_bytes(canonical(data))
    if fault == 'audit_old_tools':
        for row in audit: row['toolNames'].remove('vm_submit_handoff')
        (root / 'request-audit.jsonl').write_bytes(b'\n'.join(canonical(r) for r in audit))
    if fault == 'guest_wrong_session':
        path = kwargs['guest_directory'] / 'handoff-session-binding.json'
        data = json.loads(path.read_bytes()); data['sessionId'] = 'wrong'; path.write_bytes(canonical(data))
    with pytest.raises((ValueError, FileNotFoundError)):
        verify_handoff_execution(**kwargs, protocol='legacy-final-json' if fault == 'legacy' else 'p7-tool-submit-v1')


@pytest.mark.parametrize('evidence', ['with_submit'], indirect=True)
@pytest.mark.parametrize('fault', ['missing', 'public', 'version_bool', 'session', 'protocol', 'extra'])
def test_original_guest_activation_protocol_required(evidence, fault):
    kwargs, _, _ = evidence
    path = kwargs['guest_directory'] / 'handoff-submission-protocol.json'
    data = json.loads(path.read_bytes())
    if fault == 'missing': path.unlink()
    elif fault == 'public': path.chmod(0o644)
    else:
        if fault == 'version_bool': data['version'] = True
        if fault == 'session': data['sessionId'] = 'other'
        if fault == 'protocol': data['protocol'] = 'legacy-final-json'
        if fault == 'extra': data['extra'] = 1
        path.write_bytes(canonical(data))
    with pytest.raises((ValueError, FileNotFoundError)):
        verify_handoff_execution(**kwargs, protocol='p7-tool-submit-v1')
