"""Independent expected text projection; never writes a VM document."""
import json
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import HandoffResult, verify_result


def expected_document(submission, result, *, run_id, session_id):
    submission = HandoffSubmission.model_validate(submission)
    result = HandoffResult.model_validate(result)
    verify_result(submission, result, run_id=run_id, session_id=session_id)
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    refs = lambda statement: ', '.join(f'{c.sourceId}:{c.start}-{c.end}' for c in statement.citations)
    tasks = {task.task_id: task for task in result.tasks}
    ordered = [tasks[task.task_id] for task in submission.tasks()]
    lines = [f'项目: {quote(submission.project)}', f'截至: {submission.asOf}', '', '一、项目周报',
             '状态统计: ' + ', '.join(f'{key}={getattr(result.counts, key)}' for key in ('todo', 'doing', 'done', 'blocked'))]
    for task in ordered:
        lines.extend([f'[{task.task_id}] {quote(task.title)}',
            f'  负责人: {quote(task.owner) if task.owner else "待确认"}; 状态: {task.status}; 截止: {task.due_date}; 逾期: {"是" if task.overdue else "否"}',
            f'  进展: {quote(task.progress.text)}', f'  来源: {refs(task.progress)}'])
    lines.extend(['', '二、交接清单'])
    for task in ordered:
        lines.extend([f'[{task.task_id}] 建议: {quote(task.handoff.text)}', f'  来源: {refs(task.handoff)}'])
    lines.extend(['', '三、待确认问题'])
    for issue in result.issues:
        lines.extend([f'[{",".join(issue.taskIds)}] {issue.category}: {quote(issue.text)}', f'  来源: {refs(issue)}'])
    if not result.issues:
        lines.append('无已列出问题（不等于无风险）')
    value = ('\n'.join(lines) + '\n').encode('utf-8')
    if len(value) > 4096:
        raise ValueError('project handoff document exceeds current 4096-byte GUI limit; no truncation')
    return value
