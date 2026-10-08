"""Original task producer, simulated GUI; full trace/export transport checks."""
import copy
import io
import json
import sys
from pathlib import Path
import pytest
from backend.handoff_result import canonical, input_digest
from backend.handoff_document import expected_document
from backend.handoff_bundle import decode_handoff_bundle
from backend.handoff_draft_evidence import verify_draft_evidence
from backend.tests.test_handoff_result import fixture, RUN, SESSION
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm/tests'))
import test_handoff_trace
import test_handoff_exchanges
from desktop_control import LeaseController
from desktop_export import write_bundle
from handoff_export import build_bundle


@pytest.fixture
def protocol(request):
    source, report = fixture()
    f = test_handoff_trace.HandoffTraceTests()
    f.run_id = RUN; f.owner = '33333333-3333-3333-3333-333333333333'
    f.material_bytes = canonical(source.model_dump())
    f.document_bytes = expected_document(source, report, run_id=RUN, session_id=SESSION)
    f.draft_session_id = SESSION
    f.draft_args = [{'raw': '{broken'}, {'raw': json.dumps(report, ensure_ascii=False)}]
    if getattr(request, 'param', None) == 'submit':
        f.submit_report = report
    f.setUp()
    try:
        e = test_handoff_exchanges.HandoffExchangeTests(); e.execution_fixture = f; e.setUp()
        binding = dict(version=1, runId=RUN, owner=f.owner, epoch=1)
        session = dict(runId=RUN, sessionId=SESSION, inputSha256=input_digest(source))
        for name, value in [('handoff-session-binding.json', session)] + [
            (name, dict(status=status, binding=binding, inputSha256=input_digest(source), bytes=len(f.materials)))
            for name, status in [('handoff-input-intent.json', 'INTENT'), ('handoff-input-receipt.json', 'STORED')]]:
            path = f.task.directory / name; path.write_bytes(canonical(value)); path.chmod(0o600)
        c = LeaseController(f.task.directory / 'lease.json', run_id=RUN, owner=f.owner, epoch=1, clock=lambda:100.)
        c.revoke()
        yield f, e, c, source, report, binding, session
    finally:
        f.doCleanups()


@pytest.mark.parametrize('protocol', ['legacy', 'submit'], indirect=True)
def test_full_original_producer_trace_both_logs_export_and_independent_host(protocol):
    f, e, c, source, report, binding, session = protocol
    extra = int(hasattr(f, 'submit_report'))
    assert f.verify()['rawCalls'] == 17 + extra
    assert e.match()['officialToolCalls'] == 12 + extra
    verified = verify_draft_evidence(f.rows, e.rows, submission=source, run_id=RUN,
        session_id=SESSION, binding=session, report=report, document=f.expected)
    assert verified['status'] == 'DRAFT_EVIDENCE_MATCHED'
    if extra:
        from backend.handoff_submit_evidence import verify_submission_evidence
        assert verify_submission_evidence(f.rows, e.rows, submission=source, run_id=RUN,
            session_id=SESSION, binding=session, document=f.expected)['status'] == 'SUBMISSION_EVIDENCE_MATCHED'
    contents = build_bundle(f.task.directory, c, f.materials, f.expected)
    assert json.loads(contents['handoff-session-binding.json']) == session
    stream = io.BytesIO(); write_bundle(contents, stream)
    result = decode_handoff_bundle(stream.getvalue(), binding=binding, materials=f.materials, expected=f.expected)
    assert result['status'] == 'TRANSPORT_VERIFIED' and result['sessionVerified'] is False


@pytest.mark.parametrize('fault', ['missing', 'public', 'wrong_session', 'wrong_input'])
def test_export_requires_private_original_binding(protocol, fault):
    f, _, c, _, _, _, session = protocol
    path = f.task.directory / 'handoff-session-binding.json'
    if fault == 'missing': path.unlink()
    if fault == 'public': path.chmod(0o644)
    if fault == 'wrong_session': session['sessionId'] = 'session-44444444-4444-4444-4444-444444444444'
    if fault == 'wrong_input': session['inputSha256'] = '0' * 64
    if fault.startswith('wrong'): path.write_bytes(canonical(session))
    with pytest.raises((ValueError, OSError)):
        build_bundle(f.task.directory, c, f.materials, f.expected)


@pytest.mark.parametrize('fault', ['response', 'reject_code', 'args', 'missing', 'bool_used', 'official'])
def test_full_protocol_refuses_modified_helper_records(protocol, fault):
    f, e, *_ = protocol
    records = [r for r in f.rows if r.get('event') == 'result' and r.get('tool') == 'check_draft']
    args = [r for r in f.rows if r.get('event') == 'helper_arguments']
    if fault == 'response': records[-1]['value']['document'] += '\n'
    if fault == 'reject_code': records[0]['value']['code'] = 'SCHEMA'
    if fault == 'args': args[-1]['args']['sessionId'] = SESSION
    if fault == 'missing': f.rows.remove(args[-1])
    if fault == 'bool_used': records[-1]['value']['used'] = True
    if fault == 'official':
        call = next(r for r in e.rows if r.get('data', {}).get('name') == 'vm_check_draft')
        call['data']['arguments'] = '{"raw":"different"}'
    with pytest.raises(ValueError): e.match()
