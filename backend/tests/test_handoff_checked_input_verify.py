"""Full read-only composition with real subprocess, synthetic GUI/model images."""
import json
import pytest
from backend.handoff_result import canonical
from backend.handoff_verify import verify_handoff_execution
from backend.handoff_session import handoff_tools
from backend.tests.test_handoff_verify import evidence


@pytest.mark.parametrize('evidence',['with_checked_input'],indirect=True)
def test_checked_input_complete_combined_gates_do_not_claim_semantics(evidence):
    args, _, _ = evidence
    before = {p:p.read_bytes() for key in ('root','guest_directory','home')
              for p in args[key].rglob('*') if p.is_file()}
    result = verify_handoff_execution(**args,protocol='p7-tool-submit-v1',draft_input_mode='checked-draft-v1')
    assert result['status'] == 'EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING'
    assert result['inputMode'] == result['draft']['inputMode'] == result['submissionEvidence']['inputMode'] == 'checked-draft-v1'
    assert result['guest']['rawCalls'] == 18
    assert result['sessionVerified'] and result['guiEvidenceVerified'] and result['imageBytesVerified']
    assert not result['semanticVerified']
    assert all(p.read_bytes() == raw for p,raw in before.items())


@pytest.mark.parametrize('evidence',['with_checked_input'],indirect=True)
@pytest.mark.parametrize('fault',['default','legacy','request_missing','request_mode','binding_mode',
    'guest_missing','guest_public','guest_session','guest_version','audit_mode','audit_missing',
    'audit_tools','header_tools','model_selection','model_response','document','result','trace','image'])
def test_mode_and_original_evidence_cannot_be_inferred_or_replaced(evidence,fault):
    args, rows, audit = evidence
    root, guest = args['root'],args['guest_directory']
    mode, protocol = 'checked-draft-v1','p7-tool-submit-v1'
    if fault == 'default': mode = 'literal-text'
    elif fault == 'legacy': protocol = 'legacy-final-json'
    elif fault.startswith('request_') or fault == 'binding_mode':
        path = root / ('desktop-session-binding.json' if fault == 'binding_mode' else 'desktop-request.json')
        data = json.loads(path.read_bytes())
        if fault == 'request_missing': del data['inputMode']
        else: data['inputMode'] = 'literal-text'
        path.write_bytes(canonical(data))
    elif fault.startswith('guest_'):
        path = guest / 'handoff-input-mode.json'
        if fault == 'guest_missing': path.unlink()
        elif fault == 'guest_public': path.chmod(0o644)
        else:
            data = json.loads(path.read_bytes())
            if fault == 'guest_session': data['sessionId'] = 'other'
            else: data['version'] = True
            path.write_bytes(canonical(data))
    elif fault.startswith('audit_'):
        if fault == 'audit_mode': audit[-1]['inputMode'] = 'literal-text'
        elif fault == 'audit_missing': del audit[-1]['inputMode']
        else: audit[-1]['toolNames'].append('vm_type')
        (root/'request-audit.jsonl').write_bytes(b'\n'.join(canonical(r) for r in audit))
    elif fault in ('header_tools','model_selection','model_response'):
        if fault == 'header_tools':
            next(r for r in rows if r['type']=='request/header')['data']['header']['tools'].append(dict(name='vm_type'))
        else:
            call = next(r for r in rows if r['type']=='tool/call' and r['data']['name']=='vm_type_checked_draft')
            if fault == 'model_selection': call['data']['arguments'] = '{}'
            else: rows[rows.index(call)+1]['data']['message']['content'][0]['text'] = '{}'
        (root/'session.jsonl').write_bytes(b'\n'.join(canonical(r) for r in rows))
    else:
        if fault == 'document': path = guest / ('artifacts/handoff-'+guest.name+'.txt')
        elif fault == 'result': path = guest/'result.txt'
        elif fault == 'trace': path = guest/'trace.jsonl'
        else: path = next(root.glob('handoff-image-*.json'))
        path.write_bytes(path.read_bytes()+b'x')
    with pytest.raises((ValueError,RuntimeError,FileNotFoundError)):
        verify_handoff_execution(**args,protocol=protocol,draft_input_mode=mode)


def test_exact_mode_tools_and_invalid_protocol_pair():
    old = handoff_tools('p7-tool-submit-v1')
    new = handoff_tools('p7-tool-submit-v1','checked-draft-v1')
    assert new == (old-{'vm_type'})|{'vm_type_checked_draft'} and len(new)==10
    with pytest.raises(ValueError): handoff_tools('legacy-final-json','checked-draft-v1')
    with pytest.raises(ValueError): handoff_tools('p7-tool-submit-v1','unknown')
