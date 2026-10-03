import json
import pytest
from pydantic import ValidationError
from backend.desktop_contract import DesktopSubmission
from backend.schemas import Submission


def body(**changes):
    return dict({'kind': 'desktop-textedit', 'lines': ['交接：接口已完成', 'Next: verify']}, **changes)


def test_expected_bytes_and_json_roundtrip_preserve_exact_input():
    task = DesktopSubmission.model_validate(body(lines=['  内容不裁剪  ', 'e\u0301']))
    assert task.expected_document() == '  内容不裁剪  \ne\u0301\n'.encode()
    assert task.model_dump(mode='json')['lines'] == ['  内容不裁剪  ', 'e\u0301']
    assert DesktopSubmission.model_validate_json(task.model_dump_json()) == task
    with pytest.raises(ValidationError):
        task.kind = 'desktop-textedit'
    assert isinstance(task.lines, tuple)


@pytest.mark.parametrize('lines', [[], ['x'] * 11, [''], ['   '], ['a\nb'], ['a\rb'],
    ['\t'], ['a\0b'], ['a\x1bb'], ['a\ufeffb'], ['a\u202eb'], ['a\u2028b'],
    ['a\u2029b'], ['\ud800'], [False], [17], [None], 'not-an-array'])
def test_invalid_text_or_shape_rejected(lines):
    with pytest.raises(ValidationError):
        DesktopSubmission.model_validate(body(lines=lines))


def test_utf8_byte_limit_includes_all_line_separators():
    assert len(DesktopSubmission.model_validate(body(lines=['x' * 4095])).expected_document()) == 4096
    assert len(DesktopSubmission.model_validate(body(lines=['中' * 1365])).expected_document()) == 4096
    for lines in [['x' * 4096], ['中' * 1366], ['x' * 4094, 'y']]:
        with pytest.raises(ValidationError):
            DesktopSubmission.model_validate(body(lines=lines))


@pytest.mark.parametrize('key,value', [('path', '/tmp/result.txt'), ('application', 'Terminal'),
    ('model', 'other'), ('budget', 300), ('allowedTools', ['shell']), ('releaseAt', 'tomorrow'),
    ('inputMode', 'aggregate'), ('command', 'open'), ('expected', 'forged')])
def test_request_cannot_override_execution_authority(key, value):
    with pytest.raises(ValidationError):
        DesktopSubmission.model_validate(body(**{key: value}))


@pytest.mark.parametrize('kind', [None, 'daily-report', 'desktop', 'terminal'])
def test_unknown_kind_rejected(kind):
    with pytest.raises(ValidationError):
        DesktopSubmission.model_validate(body(kind=kind))


def test_kind_required_and_existing_daily_submission_still_rejects_desktop():
    with pytest.raises(ValidationError):
        DesktopSubmission.model_validate({'lines': ['hello']})
    with pytest.raises(ValidationError):
        Submission.model_validate(body())
    parsed = DesktopSubmission.model_validate_json(json.dumps(body()))
    assert parsed.kind == 'desktop-textedit'
