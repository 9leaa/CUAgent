"""Independent preflight for a bounded continuation of the original report task."""
import json
from pathlib import Path
from agent.daily_report import markdown, report_json, same, sha, text_file
from backend.checkpoint import EvidenceChanged, snapshot


def partial_report_plan(run, previous=None):
    run = Path(run)
    state = snapshot(run, previous)
    if state['pending']:
        raise EvidenceChanged('UNRESOLVED_SIDE_EFFECT_NO_REPLAY')
    approval = json.loads((run / 'approval.json').read_text())
    workspace = Path(approval['workspaceRoot'])
    oracle = json.loads((run / 'oracle.json').read_text())
    for name, digest in {**oracle['inputs'], 'task.json': oracle['taskSha256']}.items():
        if sha(text_file(workspace / name)[0]) != digest:
            raise EvidenceChanged('RECOVERY_INPUT_CHANGED')
    if 'report.json' not in state['artifacts']:
        raise EvidenceChanged('NO_VERIFIED_PARTIAL_REPORT')
    if not same(report_json(text_file(workspace / 'report.json')[1]), oracle['expected']):
        raise EvidenceChanged('PARTIAL_JSON_INCORRECT')
    if 'report.md' in state['artifacts'] and text_file(workspace / 'report.md')[1] != markdown(oracle['expected']):
        raise EvidenceChanged('PARTIAL_MARKDOWN_INCORRECT')
    audit = [json.loads(line) for line in Path(approval['ledgerPath']).read_bytes().splitlines()]
    writes = [row for row in audit if row['event'] == 'dispatch' and row['name'] in ('workspace_write', 'workspace_daily_report')]
    # A matching file alone is not evidence that the authorized tool produced it.
    expected_names = ['workspace_write'] + (['workspace_daily_report'] if 'report.md' in state['artifacts'] else [])
    if [row['name'] for row in writes] != expected_names:
        raise EvidenceChanged('PARTIAL_WRITE_HISTORY_AMBIGUOUS')
    for dispatch, name in zip(writes, state['artifacts']):
        returned = [row for row in audit if row['event'] == 'result' and row['callId'] == dispatch['callId']]
        if len(returned) != 1 or returned[0].get('outcome') != 'returned' or returned[0].get('artifact') != state['artifacts'][name]:
            raise EvidenceChanged('PARTIAL_WRITE_NOT_CONFIRMED')
        if dispatch['name'] == 'workspace_daily_report':
            child_id = dispatch['callId'] + ':daily-source'
            child = [row for row in audit if row['event'] == 'dispatch' and row['callId'] == child_id]
            done = [row for row in audit if row['event'] == 'result' and row['callId'] == child_id]
            if (len(child) != 1 or len(done) != 1 or child[0]['name'] != 'workspace_read'
                    or done[0].get('outcome') != 'returned' or done[0].get('artifact') != state['artifacts']['report.json']
                    or not audit.index(dispatch) < audit.index(child[0]) < audit.index(done[0]) < audit.index(returned[0])):
                raise EvidenceChanged('PARTIAL_RENDER_INTERNAL_READ_UNCONFIRMED')
    # Missing Markdown: renderer internally reads+writes, then two full reads.
    # Existing Markdown: only the two full reads. Leave no budget ambiguity.
    minimum = 4 if 'report.md' not in state['artifacts'] else 2
    if state['remaining'] < minimum:
        raise EvidenceChanged('INSUFFICIENT_CONTINUATION_BUDGET')
    return {'version': 1, 'runId': state['runId'], 'sessionId': state['sessionId'],
            'evidence': state, 'minimumCalls': minimum,
            'missing': ['report.md'] if 'report.md' not in state['artifacts'] else [],
            'instructions': '原任务恢复，已有 report.json 已独立核对，不得重写或覆盖任何文件。'
            + ('只调用 workspace_daily_report 生成缺失的 report.md。' if minimum == 4 else '两份产物均存在，不得再写入。')
            + '最后用 workspace_read 完整读回 report.json 和 report.md，然后结束；无需重复统计或读取源资料。'}
