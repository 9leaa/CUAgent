"""Trusted, model-free diagnostic sequence; caller owns lease and lifecycle.

Not registered as a model tool. This is not business acceptance and cannot
resume a failed task. All GUI/file actions go through the existing task API.
"""
import hashlib
import time

TEXT = 'P7 独立重开诊断\n保存后关闭，再重新打开并读回。'


def exercise(task, renew, *, clock=time.monotonic):
    """Run once on a fresh approved task; caller must revoke/close in finally."""
    if (task.used != 0 or task.reopen_phase is not None or task.stopped.is_set()
            or task.uncertain or task.inflight):
        raise ValueError('fresh diagnostic task required')
    deadline = clock() + 180

    def call(operation, *args):
        if clock() >= deadline:
            raise ValueError('diagnostic deadline exceeded')
        renew()  # Trusted caller; never bypasses final task admission.
        return operation(*args)

    try:
        call(task.read_materials)
        state = call(task.observe)['state']
        areas = [e for e in state['elements']
                 if e.get('role') == 'AXTextArea' and e.get('enabled', True) is True]
        if len(areas) != 1:
            raise ValueError('unique observed editor required')
        area = areas[0]
        call(task.type_text, dict(snapshot_id=state['snapshot_id'],
             element_index=area['element_index'], element_token=area['element_token'], text=TEXT))
        state = call(task.observe)['state']
        call(task.save, {'snapshot_id': state['snapshot_id']})
        state = call(task.observe)['state']
        if task.observed_value() != TEXT:
            raise ValueError('saved diagnostic text mismatch')
        call(task.reopen, {'snapshot_id': state['snapshot_id']})
        state = call(task.observe)['state']
        if task.observed_value() != TEXT:
            raise ValueError('reopened diagnostic text mismatch')
        call(task.write_result, {'snapshot_id': state['snapshot_id'], 'value': TEXT})
        if call(task.read_result)['content'] != TEXT + '\n':
            raise ValueError('diagnostic result readback mismatch')
        return {'sequenceCompleted': True, 'businessStatus': 'UNVERIFIED',
                'modelCalls': 0, 'rawCalls': task.used,
                'expectedSha256': hashlib.sha256(TEXT.encode()).hexdigest()}
    except Exception:
        task.stop()
        raise
