"""Real Driver in-flight stop diagnostic; no model/business success claim."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time

from c2_bridge import C2Task, StopRun
from driver_smoke import Calls, require_vm


def audit(directory):
    if directory.is_symlink():
        raise ValueError('Evidence directory symlink')
    ledger = directory / 'trace.jsonl'
    if ledger.is_symlink():
        raise ValueError('Evidence ledger symlink')
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    dispatches = [row for row in rows if row['event'] == 'dispatch']
    results = [row for row in rows if row['event'] == 'result']
    assert [row['used'] for row in dispatches] == list(range(1, 7))
    assert len({row['call_id'] for row in dispatches}) == len(results) == 6
    assert {row['call_id'] for row in dispatches} == {row['call_id'] for row in results}
    assert not any(row['event'] == 'UNKNOWN' for row in rows)
    action = [row for row in dispatches if row['tool'] == 'type_text']
    assert len(action) == 1
    call = action[0]['call_id']
    stopped = next(i for i, row in enumerate(rows) if row['event'] == 'stop')
    returned = next(i for i, row in enumerate(rows) if row['event'] == 'result' and row['call_id'] == call)
    held = next(i for i, row in enumerate(rows) if row['event'] == 'c2_actual_response_held')
    takeover = next(i for i, row in enumerate(rows) if row['event'] == 'c2_control' and row['reason'] == 'takeover')
    assert held < stopped < returned < takeover
    assert rows[stopped]['inflight'] == [call]
    assert not any(row['event'] == 'dispatch' for row in rows[stopped:takeover])
    assert {row['probe'] for row in rows if row['event'] == 'c2_inflight_denied'} == {'new_dispatch', 'premature_takeover'}
    recovery = [row for row in rows[takeover:] if row['event'] == 'dispatch']
    assert len(recovery) == 2 and all(row.get('recovery_observation') for row in recovery)
    states = [row['value'] for row in results if row['tool'] == 'get_window_state']
    assert len(states) == 2
    assert states[0]['pid'] == states[1]['pid'] and states[0]['window_id'] == states[1]['window_id']
    assert states[0]['snapshot_id'] != states[1]['snapshot_id']
    fields = [[e.get('value') for e in state['elements'] if e.get('role') == 'AXTextField' and e.get('label') == 'Code']
              for state in states]
    assert fields == [['cedra-42'], ['cedar-42']]
    assert all(state['screenshot_frame_valid'] and not state.get('degraded_reason') for state in states)
    assert not (directory / 'result.txt').exists() and not (directory / 'c1-submission.json').exists()
    return {'gateStatus': 'PASS', 'taskStatus': 'UNVERIFIED', 'rawCalls': 6,
            'inflightCall': call, 'singleRealInput': True, 'takeoverAfterResult': True,
            'postStopModelDispatches': 0, 'freshActualChangedField': True,
            'scope': 'real Driver return held at transport boundary; no official model cancellation or business submission'}


def exercise(task):
    ready, release = threading.Event(), threading.Event()
    errors = []
    actual = task.transport
    def held_transport(tool, args):
        value = actual(tool, args)
        if tool == 'type_text':
            task.record({'event': 'c2_actual_response_held', 'layer': 'after_actual_driver_response_before_executor_result',
                         'thread': threading.get_ident(), 'used': task.used})
            ready.set()
            if not release.wait(15):
                raise TimeoutError('Developer return hold expired; no replay')
        return value
    task.transport = held_transport
    observation = task.observe()['state']
    fields = [e for e in observation['elements'] if e.get('role') == 'AXTextField' and e.get('label') == 'Code']
    assert len(fields) == 1
    element = fields[0]
    args = {'snapshot_id': observation['snapshot_id'], 'element_index': element['element_index'],
            'element_token': element['element_token'], 'text': 'cedar-42'}
    def worker():
        try:
            with task.lock:
                task.type_text(args)
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=worker)
    thread.start()
    try:
        if not ready.wait(40):
            raise AssertionError('Actual Driver response was not observed; inspect retained error')
        assert task.used == 4 and len(task.inflight) == 1
        begun = time.monotonic()
        stopped = task.stop()
        elapsed = time.monotonic() - begun
        assert elapsed < 1 and stopped['inflight'] == sorted(task.inflight)
        assert thread.is_alive() and not errors
        for label, operation in [('new_dispatch', lambda: task.raw('get_window_state', {'pid': task.pid, 'window_id': task.window})),
                                 ('premature_takeover', task.claim_human)]:
            try:
                operation()
            except StopRun as error:
                assert error.status == 'BLOCKED'
            else:
                raise AssertionError('Unsafe request accepted: ' + label)
            assert task.used == 4 and task.owner == 'paused'
            task.record({'event': 'c2_inflight_denied', 'probe': label, 'used': task.used})
        release.set()
        thread.join(5)
        assert not thread.is_alive() and not errors and not task.inflight and not task.uncertain
        task.claim_human()
        task.recovery_observe()
        task.stop()
        return elapsed
    finally:
        release.set()
        thread.join(40)
        if thread.is_alive():
            raise RuntimeError('Work thread remains live; do not transfer control')


def run(run_id, approved):
    require_vm()
    if not approved or not re.fullmatch(r'c2_inflight_[A-Za-z0-9_-]{1,60}', run_id):
        raise ValueError('Explicit approval and fixed diagnostic identity required')
    root = Path.home() / 'C0Evidence'
    if root.is_symlink():
        raise ValueError('Evidence root symlink')
    root.mkdir(mode=0o700, exist_ok=True)
    directory = root / run_id
    with (root / 'bridge.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if directory.exists():
            raise ValueError('Fresh diagnostic directory required')
        task = C2Task(directory, transport=Calls.cli, approved=True, case_id='input_correction')
        try:
            elapsed = exercise(task)
            report = audit(directory)
            report.update(stopSeconds=elapsed, executorPid=os.getpid(), targetPid=task.pid,
                          sources={name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                   for name in ('c0_bridge.py', 'c1_bridge.py', 'c2_bridge.py', 'c2_inflight_live.py')})
            with (directory / 'inflight-audit.json').open('x') as stream:
                json.dump(report, stream, indent=2)
            print(json.dumps(report))
        finally:
            if not task.stopped.is_set():
                task.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--approve-task', action='store_true')
    args = parser.parse_args()
    run(args.run, args.approve_task)
