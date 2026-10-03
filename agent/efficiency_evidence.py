"""Read original P4 cost evidence, including failed turns. Never dispatch a model."""
import json
from pathlib import Path
from agent.daily_report import MODEL, sha
from agent.efficiency import TOKENS, number, require


def extract(run_dir):
    root = Path(run_dir)
    approval = json.loads((root / 'approval.json').read_text())
    session = (root / 'session.jsonl').read_bytes()
    ledger = Path(approval['ledgerPath']).read_bytes()
    rows = [json.loads(line) for line in session.splitlines() if line]
    audit = [json.loads(line) for line in ledger.splitlines() if line]
    lifecycle = json.loads((root / 'lifecycle.json').read_text())
    require(lifecycle.get('version') == 1 and lifecycle.get('complete') is True,
            'complete lifecycle record required')
    require(lifecycle.get('runId') == approval['runId'] and
            lifecycle.get('sessionId') == approval['sessionId'], 'lifecycle identity mismatch')
    hashes = {'sessionSha256': sha(session), 'auditSha256': sha(ledger)}
    require(all(lifecycle.get(k) == v for k, v in hashes.items()), 'original evidence changed')
    require(lifecycle.get('boundary') == 'before-activate-through-after-restore', 'wall boundary mismatch')
    start, end = lifecycle.get('startedMonotonicNs'), lifecycle.get('endedMonotonicNs')
    require(type(start) is int and type(end) is int and 0 <= start < end, 'monotonic lifecycle required')
    interventions = lifecycle.get('interventions')
    require(isinstance(interventions, list) and all(isinstance(i, dict) and
            isinstance(i.get('kind'), str) and i['kind'] and type(i.get('monotonicNs')) is int and
            start <= i['monotonicNs'] <= end for i in interventions), 'explicit intervention record required')
    starts = [r for r in rows if r['type'] == 'turn/start']
    ends = [r for r in rows if r['type'] == 'turn/end']
    require(len(starts) == len(ends) == 1, 'one original terminal turn required; never discard retries')
    require(ends[0]['data']['reason']['kind'] in ('completed', 'error', 'aborted'), 'unknown terminal reason')
    elapsed = ends[0]['time'] - starts[0]['time']
    wall = (end - start) / 1_000_000
    require(number(elapsed) and wall >= elapsed, 'inconsistent wall or turn time')
    messages = [r['data'] for r in rows if r['type'] == 'assistant/message']
    require(messages and all(isinstance(m.get('usage'), dict) and
            all(type(m['usage'].get(k)) is int and m['usage'][k] >= 0 for k in TOKENS)
            for m in messages), 'usage incomplete; never assume zero')
    require(all(m['usage']['totalTokens'] == sum(m['usage'][k] for k in TOKENS[:-1])
                for m in messages), 'inconsistent per-message usage')
    usage = {k: sum(m['usage'][k] for m in messages) for k in TOKENS}
    dispatch = [a for a in audit if a['event'] == 'dispatch']
    calls = [r for r in rows if r['type'] == 'tool/call']
    headers = [r['data']['header'] for r in rows if r['type'] == 'request/header']
    issues = []
    if not headers or not all(all(h['config'].get(k) == v for k, v in MODEL.items()) for h in headers):
        issues.append('model/thinking mismatch')
    allowed = set(approval['allowedTools'])
    if any(not {t['name'] for t in h['tools']} <= allowed for h in headers):
        issues.append('unapproved model capability')
    if any(block.get('type') == 'reasoning' and block.get('text') for m in messages
           for block in m.get('message', {}).get('content', [])):
        issues.append('unexpected reasoning output')
    if any(a.get('runId') != approval['runId'] or a.get('sessionId') != approval['sessionId'] for a in audit):
        issues.append('audit identity mismatch')
    if len(dispatch) > 30 or [a.get('used') for a in dispatch] != list(range(1, len(dispatch) + 1)):
        issues.append('non-continuous or exceeded budget')
    if len({a['callId'] for a in dispatch}) != len(dispatch):
        issues.append('duplicate dispatch')
    if any(a['name'] not in allowed for a in dispatch):
        issues.append('unapproved dispatch')
    return {**hashes, 'terminalReason': ends[0]['data']['reason'], 'safetyIssues': issues,
            'attempt': {'attemptId': approval['sessionId'] + ':turn-1', 'usage': usage,
                        'calls': len(calls), 'rawCalls': len(dispatch), 'elapsedMs': elapsed,
                        'wallMs': wall, 'interventions': len(interventions)}}
