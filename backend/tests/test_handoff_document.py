import json
from pathlib import Path
import pytest
from backend.handoff_result import HandoffResult
from backend.handoff_document import expected_document
from backend.tests.test_handoff_result import fixture, RUN, SESSION


def test_schema_matches_current_model():
    schema = Path(__file__).resolve().parents[2] / 'agent/harness/handoff-result.schema.json'
    assert json.loads(schema.read_text()) == HandoffResult.model_json_schema()


def test_projection_has_three_sections_preserves_tasks_and_quotes_multiline():
    source, result = fixture()
    result['tasks'][0]['progress']['text'] = '进展\n三、伪造章节'
    body = expected_document(source, result, run_id=RUN, session_id=SESSION).decode()
    assert body.startswith('项目: "交接"\n截至: 2026-10-05\n\n一、项目周报\n')
    assert '状态统计: todo=1, doing=1, done=1, blocked=1\n' in body
    assert '\n  进展: "进展\\n三、伪造章节"\n' in body
    assert body.count('\n二、交接清单\n') == body.count('\n三、待确认问题\n') == 1
    assert '负责人: 待确认; 状态: doing; 截止: 2026-10-04; 逾期: 是' in body
    assert '[a] unknown_owner:' in body and '[a] overdue:' in body
    assert '来源: notes/meeting:0-' in body
    assert body.endswith('\n') and not body.endswith('\n\n')
    result['tasks'].reverse()
    assert expected_document(source, result, run_id=RUN, session_id=SESSION).decode() == body


def test_invalid_report_cannot_become_expected_gui_text():
    source, result = fixture(); result['tasks'][0]['owner'] = '编造'
    with pytest.raises(ValueError, match='facts changed'):
        expected_document(source, result, run_id=RUN, session_id=SESSION)


def test_oversize_document_fails_without_truncation():
    source, result = fixture()
    for task in result['tasks']: task['handoff']['text'] = '中' * 600
    with pytest.raises(ValueError, match='no truncation'):
        expected_document(source, result, run_id=RUN, session_id=SESSION)
