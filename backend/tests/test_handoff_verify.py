"""Real local composition/subprocess, simulated Driver/model/attachment evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import pytest
from backend.handoff_document import expected_document
from backend.handoff_result import canonical, input_digest
from backend.handoff_verify import verify_handoff_execution, verify_request_audit, MODEL, TOOLS
from backend.tests.test_handoff_result import fixture, RUN, SESSION

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm/tests'))
import test_handoff_trace
import test_handoff_exchanges


@pytest.fixture
def evidence(tmp_path, request):
    configured = getattr(request, 'param', None)
    with_submit = configured == 'with_submit' or type(configured) is dict and configured.get('protocol') == 'p7-tool-submit-v1'
    with_draft = with_submit or getattr(request, 'param', None) == 'with_draft'
    tools = TOOLS | {'vm_submit_handoff'} if with_submit else TOOLS
    source, report = request.param if hasattr(request, 'param') and not with_draft else fixture()
    if type(configured) is dict:
        source, report = configured['source'], configured['report']
    executor = test_handoff_trace.HandoffTraceTests()
    executor.run_id, executor.material_bytes = RUN, canonical(source.model_dump())
    executor.document_bytes = expected_document(source, report, run_id=RUN, session_id=SESSION)
    if with_draft:
        executor.draft_session_id = SESSION
        executor.draft_args = [{'raw': '{broken'}, {'raw': json.dumps(report, ensure_ascii=False)}]
    if with_submit:
        executor.submit_report = report
    executor.setUp()
    try:
        exchange = test_handoff_exchanges.HandoffExchangeTests()
        exchange.execution_fixture = executor; exchange.setUp()
        root = tmp_path / RUN; root.mkdir(mode=0o700)
        home = tmp_path / 'home'; home.mkdir(mode=0o700)
        binding = dict(version=1, runId=RUN, owner='worker', epoch=1)
        def save(path, value):
            path.write_bytes(value if type(value) is bytes else json.dumps(value, ensure_ascii=False).encode())
            path.chmod(0o600)
        if with_draft:
            save(executor.task.directory / 'handoff-session-binding.json',
                 dict(runId=RUN, sessionId=SESSION, inputSha256=input_digest(source)))
        for name, status in [('handoff-input-intent.json', 'INTENT'), ('handoff-input-receipt.json', 'STORED')]:
            save(executor.task.directory / name, dict(status=status, binding=binding,
                inputSha256=input_digest(source), bytes=len(executor.material_bytes)))
        image = b'RIFF\x04\x00\x00\x00WEBP'; sha = hashlib.sha256(image).hexdigest()
        directory = home
        for part in ('attachments', 'v1', 'objects', sha[:2]):
            directory = directory / part; directory.mkdir(mode=0o700)
        save(directory / sha, image)
        for row in exchange.rows:
            if row['type'] != 'tool/result': continue
            content = row['data']['message']['content']
            if len(content) != 2: continue
            state = json.loads(content[0]['text'])
            metadata = dict(attachmentId='sha256:'+sha, mediaType='image/webp', bytes=len(image), width=1, height=1)
            content[1]['attachment'] = metadata
            png = (executor.task.directory / ('state-%02d.png' % state['used'])).read_bytes()
            save(root / ('handoff-image-%02d.json' % state['used']), dict(version=1, runId=RUN, sessionId=SESSION,
                inputSha256=input_digest(source), snapshotId=state['snapshot_id'], used=state['used'],
                source=dict(sha256=hashlib.sha256(png).hexdigest(), bytes=len(png)), attachment=metadata))
        prompt = dict(sessionId=SESSION, requestId='original', mode='queue', content=[dict(type='text', text='frozen original prompt')])
        saved_binding = dict(kind='project-handoff', runId=RUN, sessionId=SESSION,
            cwd=str(root / 'workspace'), inputSha256=input_digest(source))
        if with_submit:
            saved_binding['protocol'] = 'p7-tool-submit-v1'
            save(root / 'desktop-request.json', saved_binding)
        save(root / 'desktop-session-binding.json', saved_binding)
        save(root / 'prompt-request.json', dict(request=prompt))
        rows = [dict(type='session', version=4, id=SESSION, cwd=str(root / 'workspace'), agentPreset='project-handoff', isSeeded=False, delegationDepth=0),
            dict(type='turn/start', data=dict(turn=1)),
            dict(type='user/message', data=dict(role='user', source=dict(kind='user', rpcId='original'), content=prompt['content'])),
            dict(type='request/header', data=dict(header=dict(config=MODEL.copy(), tools=[dict(name=t) for t in sorted(tools)])))]
        audit, ids = [], []
        def assistant(content):
            audit.append(dict(at='2026-10-05T04:00:00+00:00', runId=RUN, sessionId=SESSION,
                inputSha256=input_digest(source), provider=MODEL['provider'], model=MODEL['model'],
                toolNames=sorted(tools), imageBlocks=len(ids), imageAttachmentIds=list(ids)))
            rows.append(dict(type='assistant/message', data=dict(turn=1, step=len(audit), message=dict(id=str(len(audit)),
                role='assistant', source=dict(kind='model', provider=MODEL['provider'], model=MODEL['model']), content=content))))
        for index in range(0, len(exchange.rows), 2):
            call, result = copy.deepcopy(exchange.rows[index:index+2]); data = call['data']
            assistant([dict(type='tool-call', id=data['callId'], name=data['name'], arguments=data['arguments'])])
            rows.extend([call, result])
            ids.extend(b['attachment']['attachmentId'] for b in result['data']['message']['content'] if b['type'] == 'image')
        if not with_submit:
            assistant([dict(type='text', text=json.dumps(report, ensure_ascii=False))])
        rows.append(dict(type='turn/end', data=dict(turn=1, reason=dict(kind='completed'))))
        for seq, row in enumerate(rows[1:]): row['seq'] = seq
        save(root / 'session.jsonl', b'\n'.join(canonical(r) for r in rows))
        save(root / 'request-audit.jsonl', b'\n'.join(canonical(r) for r in audit))
        yield dict(root=root, guest_directory=executor.task.directory, home=home, submission=source, session_id=SESSION, binding=binding), rows, audit
    finally:
        executor.doCleanups()


def test_combined_actual_readonly_subprocess_and_all_gates(evidence):
    args, _, _ = evidence
    files = {p: p.read_bytes() for directory in (args['root'], args['guest_directory'], args['home']) for p in directory.rglob('*') if p.is_file()}
    result = verify_handoff_execution(**args)
    assert result['status'] == 'EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING'
    assert result['sessionVerified'] is result['guiEvidenceVerified'] is result['imageBytesVerified'] is True
    assert result['semanticVerified'] is False
    assert result['guest']['rawCalls'] == 15
    assert result['audit']['requests'] == 11
    assert all(path.read_bytes() == raw for path, raw in files.items())


@pytest.mark.parametrize('evidence', ['with_draft'], indirect=True)
def test_complete_composition_with_rejected_then_valid_draft(evidence):
    args, _, _ = evidence
    result = verify_handoff_execution(**args)
    assert result['status'] == 'EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING'
    assert result['draft']['status'] == 'DRAFT_EVIDENCE_MATCHED'
    assert result['draft']['calls'] == 2 and result['guest']['rawCalls'] == 17
    assert result['audit']['requests'] == 13 and result['semanticVerified'] is False


@pytest.mark.parametrize('fault', ['session', 'binding', 'prompt', 'audit', 'image-record', 'guest-document', 'attachment'])
def test_each_original_evidence_gate_is_required(evidence, fault):
    args, _, _ = evidence; root = args['root']
    if fault == 'session': path = root / 'session.jsonl'
    elif fault == 'binding': path = root / 'desktop-session-binding.json'
    elif fault == 'prompt': path = root / 'prompt-request.json'
    elif fault == 'audit': path = root / 'request-audit.jsonl'
    elif fault == 'image-record': path = root / 'handoff-image-04.json'
    elif fault == 'guest-document': path = args['guest_directory'] / ('artifacts/handoff-'+RUN+'.txt')
    else: path = next(p for p in args['home'].rglob('*') if p.is_file())
    path.write_bytes(path.read_bytes() + b'x')
    with pytest.raises((ValueError, RuntimeError)): verify_handoff_execution(**args)


@pytest.mark.parametrize('fault', ['run', 'session', 'input', 'model', 'tools', 'image-count', 'image-id', 'missing', 'time'])
def test_request_audit_proves_exact_original_images_each_step(evidence, fault):
    args, rows, audit = evidence
    if fault == 'run': audit[-1]['runId'] = 'other'
    elif fault == 'session': audit[-1]['sessionId'] = 'other'
    elif fault == 'input': audit[-1]['inputSha256'] = '0'*64
    elif fault == 'model': audit[-1]['model'] = 'other'
    elif fault == 'tools': audit[-1]['toolNames'].append('shell')
    elif fault == 'image-count': audit[-1]['imageBlocks'] = True
    elif fault == 'image-id': audit[-1]['imageAttachmentIds'][-1] = 'sha256:'+'0'*64
    elif fault == 'missing': audit.pop()
    else: audit[-1]['at'] = '2026-10-05T03:00:00+00:00'
    with pytest.raises(ValueError): verify_request_audit(b'\n'.join(canonical(r) for r in audit), rows,
        run_id=RUN, session_id=SESSION, input_sha256=input_digest(args['submission']))
