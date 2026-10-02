"""Read-only evidence snapshots; these never replace the execution ledger."""
import hashlib
import json
from pathlib import Path


class EvidenceChanged(ValueError):
    pass


def snapshot(run, previous=None):
    run = Path(run)
    approval = json.loads((run / 'approval.json').read_text())
    ledger = Path(approval['ledgerPath'])
    if ledger.is_symlink():
        raise EvidenceChanged('AUDIT_PATH_CHANGED')
    raw = ledger.read_bytes() if ledger.exists() else b''
    if raw and not raw.endswith(b'\n'):
        raise EvidenceChanged('AUDIT_PARTIAL_RECORD')
    if previous:
        if previous['runId'] != approval['runId'] or previous['sessionId'] != approval['sessionId']:
            raise EvidenceChanged('CHECKPOINT_IDENTITY_CHANGED')
        size = previous['auditBytes']
        if len(raw) < size or hashlib.sha256(raw[:size]).hexdigest() != previous['auditSha256']:
            raise EvidenceChanged('AUDIT_PREFIX_CHANGED')
    rows = [json.loads(line) for line in raw.splitlines()]
    used, pending, seen = 0, {}, set()
    for row in rows:
        if row.get('runId') != approval['runId'] or row.get('sessionId') != approval['sessionId']:
            raise EvidenceChanged('AUDIT_IDENTITY_CHANGED')
        kind = row.get('event')
        if kind == 'dispatch':
            call_id = row['callId']
            used += 1
            if row['used'] != used or used > 30 or call_id in seen:
                raise EvidenceChanged('AUDIT_DISPATCH_CHANGED')
            seen.add(call_id)
            pending[call_id] = row['name']
        elif kind == 'result':
            if pending.get(row['callId']) != row['name']:
                raise EvidenceChanged('AUDIT_RESULT_CHANGED')
            del pending[row['callId']]
        elif kind not in ('request', 'denied'):
            raise EvidenceChanged('AUDIT_EVENT_CHANGED')
    artifacts = {}
    workspace = Path(approval['workspaceRoot']).resolve(strict=True)
    for name in ('report.json', 'report.md'):
        path = workspace / name
        if path.is_symlink():
            raise EvidenceChanged('ARTIFACT_PATH_CHANGED')
        if path.exists():
            content = path.read_bytes()
            artifacts[name] = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
    if previous and any(artifacts.get(name) != value for name, value in previous['artifacts'].items()):
        raise EvidenceChanged('CHECKPOINT_ARTIFACT_CHANGED')
    return {'version': 1, 'runId': approval['runId'], 'sessionId': approval['sessionId'],
            'auditBytes': len(raw), 'auditSha256': hashlib.sha256(raw).hexdigest(),
            'used': used, 'remaining': 30 - used, 'pending': pending, 'artifacts': artifacts}
