"""Real HTTP and ledger; synthetic input prerequisite and simulated Driver."""
import copy
from functools import partial
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_calc_save_task as base
from calc_save_model_task import CalcSaveModelTask
from test_calc_edit import fixture
from test_calc_model_http import service as http_service, SESSION


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    _, regions = fixture()
    original = base.snapshot_fixture
    def snapshot():
        state, args = original()
        state['elements'][2]['frame'] = dict(x=110, y=60, w=40, h=10)
        return state, args
    monkeypatch.setattr(base, 'snapshot_fixture', snapshot)
    monkeypatch.setattr(base, 'CalcSaveTask', partial(CalcSaveModelTask,
        session_id=SESSION, name_box_grid=[0, 0, 100, 40],
        controls_region=regions['controls_region'], editor_regions=regions['editor_regions']))
    yield from base.save_task.__wrapped__(tmp_path)


@pytest.fixture
def service(adapter):
    yield from http_service.__wrapped__(adapter)


def input_prerequisite(task):
    source, _ = fixture()
    for item in source['elements'][1:]:
        element = copy.deepcopy(item)
        element['element_index'] += 10
        element['element_token'] = task.snapshot['snapshot_id'] + ':' + str(element['element_index'])
        if element['role'] == 'AXTextArea':
            element['value'] = task.input_text
        task.snapshot['elements'].append(element)
    task.before_input = 'earlier-input-snapshot'
    task.phase = 'AWAITING_INPUT_CONFIRMATION'
    task.confirm_input(snapshot_id=task.snapshot['snapshot_id'], name_box_index=2, **task.input_regions)


@pytest.mark.parametrize('point',[False,True])
def test_commit_confirm_then_save_over_http(adapter, service, point):
    task, calls, *_ = adapter
    input_prerequisite(task)
    code, committed = service('commit_cell', dict(snapshot_id=task.snapshot['snapshot_id']))
    assert code == 200 and committed['status'] == 'CELL_COMMIT_OBSERVED'
    assert committed['commitEffectVerified'] and not committed['saved']
    assert task.phase == 'COMMIT_CONFIRMED' and not task.stopped.is_set()
    args=dict(snapshot_id=committed['state']['snapshot_id'])
    if point:args.update(x=140,y=50)
    code, opened = service('open_save_dialog', args)
    assert code == 200 and opened['protocol'] == 'calc-save-v1'
    assert opened['status'] == 'SAVE_DIALOG_ATTEMPT_OBSERVED' and not opened['saved']
    assert task.used == 5 and len(calls) == 5
    if point:assert calls[3][1]['delivery_mode']=='foreground' and 'element_token' not in calls[3][1]
    assert service('open_save_dialog', dict(snapshot_id=opened['state']['snapshot_id']))[0] == 409
    assert len(calls) == 5 and task.stopped.is_set()


@pytest.mark.parametrize('fault', ['path', 'target', 'snapshot', 'session', 'run', 'raw', 'phase'])
def test_save_http_cannot_expand_scope(adapter, service, fault):
    task, calls, *_ = adapter
    args = dict(snapshot_id=task.snapshot['snapshot_id']); changes = {}; op = 'open_save_dialog'
    if fault == 'path': args['destination'] = '/tmp/other.ods'
    elif fault == 'target': args['element_token'] = 's00000001:4'
    elif fault == 'snapshot': args['snapshot_id'] = 'old'
    elif fault == 'session': changes['sessionId'] = 'other'
    elif fault == 'run': changes['runId'] = 'other'
    elif fault == 'raw': op = 'open_save'
    elif fault == 'phase': task.phase = 'INPUT_OBSERVED'
    assert service(op, args, **changes)[0] == 409
    assert task.stopped.is_set() and len(calls) == 1


def test_failed_post_commit_never_opens_save(adapter, service, monkeypatch):
    task, calls, *_ = adapter
    input_prerequisite(task)
    original = task.transport
    def transport(tool, args):
        result = original(tool, args)
        if tool == 'get_window_state': result['elements'][1]['value'] = 'wrong'
        return result
    monkeypatch.setattr(task, 'transport', transport)
    assert service('commit_cell', dict(snapshot_id=task.snapshot['snapshot_id']))[0] == 409
    assert task.stopped.is_set() and len(calls) == 3
    assert service('open_save_dialog', dict(snapshot_id='any'))[0] == 409
    assert len(calls) == 3
