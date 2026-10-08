"""Compose original execution gates. Never claim semantic or product success."""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from datetime import datetime
from backend.desktop_collect import private_path, run_bounded
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical, input_digest
from backend.handoff_session import extract_handoff_result, strict_json, require, MODEL, TOOLS, handoff_tools
from backend.handoff_attachments import read_handoff_attachments
from backend.handoff_images import verify_handoff_images
from backend.handoff_draft_evidence import verify_draft_evidence
from backend.handoff_submit_evidence import verify_submission_evidence


def verify_request_audit(raw, rows, *, run_id, session_id, input_sha256, protocol='legacy-final-json',
                         draft_input_mode='literal-text'):
    tools = handoff_tools(protocol, draft_input_mode)
    require(type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024)
    audit = [strict_json(line.decode()) for line in raw.splitlines()]
    assistants = [r for r in rows if r['type'] == 'assistant/message']
    require(0 < len(audit) == len(assistants) <= 31)
    images, index, last = [], 0, None
    for row in rows:
        if row['type'] == 'tool/result':
            images.extend(block['attachment']['attachmentId'] for block in row['data']['message']['content'] if block['type'] == 'image')
        elif row['type'] == 'assistant/message':
            record = audit[index]; index += 1
            require(type(record) is dict)
            require(record.get('inputMode') == draft_input_mode if draft_input_mode == 'checked-draft-v1'
                    else 'inputMode' not in record)
            require(type(record) is dict and record.get('runId') == run_id and record.get('sessionId') == session_id
                    and record.get('inputSha256') == input_sha256 and record.get('provider') == MODEL['provider']
                    and record.get('model') == MODEL['model'] and sorted(record['toolNames']) == sorted(tools)
                    and type(record.get('imageBlocks')) is int and record['imageBlocks'] == len(images)
                    and record.get('imageAttachmentIds') == images)
            at = datetime.fromisoformat(record['at'])
            require(at.tzinfo is not None and (last is None or at >= last)); last = at
    require(bool(images))
    return dict(requests=len(audit), sha256=hashlib.sha256(raw).hexdigest(), requestImagesVerified=True)


def verify_handoff_execution(root, *, guest_directory, home, submission, session_id, binding,
                             protocol='legacy-final-json', draft_input_mode='literal-text'):
    """Trusted collector must already have revoked execution and frozen files.

    A supplied folder or self-consistent bundle does not establish SSH provenance.
    This is an offline composition gate, not the production dispatch adapter.
    """
    handoff_tools(protocol, draft_input_mode)
    root, guest_directory = private_path(root, directory=True), private_path(guest_directory, directory=True)
    submission = HandoffSubmission.model_validate(submission)
    require(root.name == binding['runId'] == guest_directory.name)
    originals = {}
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode, info.st_nlink, info.st_uid)
    def read(path, limit, private=True):
        require(path.resolve(strict=True) == path)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                    and (not private or not info.st_mode & 0o077) and 0 < info.st_size <= limit)
            raw = stream.read(info.st_size + 1)
            require(len(raw) == info.st_size and signature(os.fstat(stream.fileno())) == signature(info))
        require(signature(path.stat(follow_symlinks=False)) == signature(info))
        if path in originals: require(originals[path][:2] == (raw, signature(info)))
        else: originals[path] = (raw, signature(info), limit, private)
        return raw
    digest = input_digest(submission)
    saved = strict_json(read(root / 'desktop-session-binding.json', 32768).decode())
    expected_binding = dict(kind='project-handoff', runId=root.name, sessionId=session_id,
                            cwd=str(root / 'workspace'), inputSha256=digest)
    if draft_input_mode == 'checked-draft-v1':
        expected_binding['inputMode'] = draft_input_mode
        require(canonical(strict_json(read(guest_directory / 'handoff-input-mode.json', 4096).decode())) ==
                canonical(dict(version=1, inputMode=draft_input_mode, runId=root.name,
                               sessionId=session_id, inputSha256=digest)))
    if protocol == 'p7-tool-submit-v1':
        expected_binding['protocol'] = protocol
        require(strict_json(read(root / 'desktop-request.json', 32768).decode()) == expected_binding)
    require(saved == expected_binding)
    prompt = strict_json(read(root / 'prompt-request.json', 65536).decode())['request']
    raw = read(root / 'session.jsonl', 64 * 1024 * 1024)
    extracted = extract_handoff_result(raw, submission=submission, run_id=root.name,
        session_id=session_id, cwd=saved['cwd'], prompt=prompt, protocol=protocol, draft_input_mode=draft_input_mode)
    trace_raw = read(guest_directory / 'trace.jsonl', 8 * 1024 * 1024)
    trace = [strict_json(line.decode()) for line in trace_raw.splitlines()]
    official = [strict_json(line.decode()) for line in raw.splitlines()]
    draft = None
    submitted = None
    if (any(r.get('tool') == 'check_draft' for r in trace)
            or any(r.get('type') == 'tool/call' and r.get('data', {}).get('name') == 'vm_check_draft' for r in official)):
        draft = verify_draft_evidence(trace, official, submission=submission, run_id=root.name,
            session_id=session_id, binding=strict_json(read(guest_directory / 'handoff-session-binding.json', 4096).decode()),
            report=extracted['report'], document=extracted['document'], draft_input_mode=draft_input_mode)
    if protocol == 'p7-tool-submit-v1':
        require(canonical(strict_json(read(guest_directory / 'handoff-submission-protocol.json', 4096).decode())) ==
                canonical(dict(version=1, protocol=protocol, runId=root.name, sessionId=session_id, inputSha256=digest)))
        submitted = verify_submission_evidence(trace, official, submission=submission, run_id=root.name,
            session_id=session_id, binding=strict_json(read(guest_directory / 'handoff-session-binding.json', 4096).decode()),
            document=extracted['document'], draft_input_mode=draft_input_mode)
        require(canonical(submitted['report']) == canonical(extracted['report']))
    payload = json.dumps(dict(binding=binding, materialsBase64=base64.b64encode(canonical(submission.model_dump())).decode(),
        expectedBase64=base64.b64encode(extracted['document']).decode())).encode()
    command = Path(__file__).resolve().parents[1] / 'tools/mac_vm/handoff_inspect.py'
    output = run_bounded([sys.executable, str(command), '--directory', str(guest_directory), '--session', str(root / 'session.jsonl'),
                         '--draft-input-mode', draft_input_mode],
                         payload, limit=1024*1024, timeout=30, input_limit=512*1024)
    inspected = strict_json(output.decode())
    if draft_input_mode == 'checked-draft-v1':
        require(inspected['guest'].get('inputMode') == inspected['exchanges'].get('inputMode') == draft_input_mode)
    require(inspected['sessionSha256'] == extracted['sessionSha256']
            and inspected['guest']['files']['trace.jsonl']['sha256'] == hashlib.sha256(trace_raw).hexdigest()
            and inspected['guest']['status'] == 'VM_EVIDENCE_VERIFIED'
            and inspected['exchanges']['status'] == 'EXCHANGES_MATCHED'
            and inspected['exchanges']['officialToolCalls'] == extracted['officialToolCalls'])
    observations = inspected['exchanges']['attachmentsToVerify']
    records, pngs = [], {}
    for observation in observations:
        used = observation['used']
        require(type(used) is int and 1 <= used <= 30)
        records.append(read(root / ('handoff-image-%02d.json' % used), 4096))
        name = 'state-%02d.png' % used
        data = read(guest_directory / name, 8*1024*1024, private=False)
        require(inspected['guest']['files'][name] == dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
        pngs[name] = data
    images = verify_handoff_images(records, observations, pngs, read_handoff_attachments(home, observations),
        run_id=root.name, session_id=session_id, input_sha256=digest)
    audit = verify_request_audit(read(root / 'request-audit.jsonl', 8*1024*1024),
        [strict_json(line.decode()) for line in raw.splitlines()], run_id=root.name, session_id=session_id,
        input_sha256=digest, protocol=protocol, draft_input_mode=draft_input_mode)
    for path, (_, _, limit, private) in originals.items(): read(path, limit, private)
    return dict(status='EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING', runId=root.name, sessionId=session_id,
        sessionVerified=True, guiEvidenceVerified=True, imageBytesVerified=True, semanticVerified=False,
        result=extracted['report'], structure=extracted['structure'], sessionSha256=extracted['sessionSha256'],
        documentSha256=hashlib.sha256(extracted['document']).hexdigest(), guest=inspected['guest'], images=images, audit=audit,
        draft=draft, **({'protocol': protocol, 'submissionEvidence': submitted} if submitted else {}),
        **({'inputMode': draft_input_mode} if draft_input_mode == 'checked-draft-v1' else {}))
