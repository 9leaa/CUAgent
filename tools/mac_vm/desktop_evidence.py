"""Read-only VM evidence inspection. Does not prove the official model session."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

from real_app_verifier import verify_evidence
from real_app_bridge import body_from_state


def require(condition):
    if not condition:
        raise ValueError('DESKTOP_GUEST_EVIDENCE_UNVERIFIED')


def inspect_guest_evidence(directory, *, run_id, expected):
    """Caller must revoke execution and confirm no in-flight calls before collection.

    Hashes detect changed collected bytes, not a malicious VM owner. Source data
    must travel over the trusted collection channel, never a model-supplied bundle.
    """
    require(isinstance(run_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run_id))
    require(isinstance(expected, bytes) and 0 < len(expected) <= 4096)
    root = Path(directory).absolute()
    require(root.resolve(strict=True) == root and root.name == run_id)
    info = root.stat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077)
    collected = {}
    total = 0

    def read(name, limit):
        nonlocal total
        path = root / name
        require(path.resolve(strict=True) == path and path.is_relative_to(root))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid() and before.st_size <= limit)
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        require(len(data) == before.st_size and (before.st_size, before.st_mtime_ns, before.st_ino)
                == (after.st_size, after.st_mtime_ns, after.st_ino))
        total += len(data)
        require(total <= 64 * 1024 * 1024)
        collected[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        return data

    trace = read('trace.jsonl', 8 * 1024 * 1024)
    rows = [json.loads(line) for line in trace.splitlines()]
    require(bool(rows))
    calls, returned, positions = {}, {}, {}
    stopped = False
    last_at = -math.inf
    for index, row in enumerate(rows):
        require(isinstance(row, dict) and row.get('run_id') == run_id)
        at = row.get('at')
        require(type(at) in (int, float) and math.isfinite(at) and at >= last_at)
        last_at = at
        event = row.get('event')
        require(event != 'UNKNOWN')
        if event == 'stop':
            stopped = True
        if event == 'dispatch':
            identity = row.get('call_id')
            require(not stopped and isinstance(identity, str) and identity not in calls)
            require(len(calls) == len(returned))  # Original bridge dispatches serially.
            require(type(row.get('used')) is int and row['used'] == len(calls) + 1 <= 30)
            calls[identity] = row
            positions[identity] = index
        elif event in ('result', 'error'):
            identity = row.get('call_id')
            require(isinstance(identity, str) and identity in calls and identity not in returned)
            require(calls[identity].get('tool') == row.get('tool'))
            returned[identity] = row
    require(bool(calls) and calls.keys() == returned.keys())
    observations = {}
    observed_calls = set()
    by_used = {row['used']: key for key, row in calls.items()}
    for index, row in enumerate(rows):
        if row.get('event') != 'observation_evidence':
            continue
        used = row.get('used')
        require(type(used) is int and used in by_used)
        key = by_used[used]
        require(key not in observed_calls)
        observed_calls.add(key)
        result = returned[key]
        require(calls[key]['tool'] == 'get_window_state' and result['event'] == 'result')
        state = result.get('value')
        require(isinstance(state, dict) and state.get('snapshot_id') == row.get('snapshot_id'))
        snapshot = row['snapshot_id']
        require(isinstance(snapshot, str) and snapshot not in observations and result['at'] <= row['at'])
        require(rows.index(result) < index and state.get('screenshot_frame_valid') is True)
        require(state.get('app_name') == 'TextEdit' and state.get('window_title') == 'handoff-' + run_id + '.txt')
        files = row.get('files')
        require(isinstance(files, dict) and set(files) == {'json', 'png'})
        for extension in ('json', 'png'):
            name = 'state-%02d.' % used + extension
            data = read(name, 8 * 1024 * 1024)
            require(collected[name] == files[extension])
            if extension == 'json':
                require(json.loads(data) == state)
            else:
                require(data.startswith(b'\x89PNG\r\n\x1a\n'))
        observations[snapshot] = (index, state)
    require(bool(observations))
    require(observed_calls == {key for key in calls if calls[key]['tool'] == 'get_window_state'
                               and returned[key]['event'] == 'result'})
    for index, row in enumerate(rows):
        if row.get('event') not in ('attempted_input', 'attempted_save'):
            continue
        snapshot = row.get('snapshot_id')
        require(snapshot in observations)
        source_index = observations[snapshot][0]
        tool = 'type_text' if row['event'] == 'attempted_input' else 'hotkey'
        candidates = [key for key in calls if calls[key]['tool'] == tool and source_index < positions[key] < index]
        require(len(candidates) == 1 and rows.index(returned[candidates[0]]) < index)
        require(not any(other['event'] == 'dispatch' for other in rows[source_index + 1:positions[candidates[0]]]))
    final = json.loads(read('final_state.json', 8 * 1024 * 1024))
    require(isinstance(final, dict) and final.get('snapshot_id') in observations)
    final_index, original = observations[final['snapshot_id']]
    require(final == original)
    saves = [index for index, row in enumerate(rows) if row.get('event') == 'attempted_save']
    require(bool(saves) and final_index > max(saves))
    writes = [key for key, row in calls.items() if row['tool'] == 'write_result']
    reads = [key for key, row in calls.items() if row['tool'] == 'read_result']
    require(len(writes) == 1 and reads and final_index < positions[writes[0]] < min(positions[key] for key in reads))
    write_index = positions[writes[0]]
    # final_state is captured by write_result, not by subsequent observations.
    require(final_index == max(index for index, _ in observations.values() if index < write_index))
    require(not any(row['event'] == 'dispatch' for row in rows[final_index + 1:write_index]))
    final_call = next(key for key in observed_calls
                      if returned[key]['value']['snapshot_id'] == final['snapshot_id'])
    require(0 <= calls[writes[0]]['at'] - returned[final_call]['at'] <= 30)
    for key, call in calls.items():
        if positions[key] > write_index:
            require(call['tool'] in {'get_window_state', 'read_result'} and returned[key]['event'] == 'result')
    for index, state in observations.values():
        if index > write_index:
            require(all(state.get(field) == final.get(field) for field in ('pid', 'window_id')))
            displayed = body_from_state(state).encode('utf8')
            require(expected in (displayed, displayed + b'\n'))
    document = read('artifacts/handoff-' + run_id + '.txt', 4096)
    result_bytes = read('result.txt', 4097)
    business = verify_evidence(rows, expected, document, result_bytes, final)
    require(business['status'] == 'SUCCEEDED')
    # Catch concurrent ledger changes; production collection additionally freezes
    # the source after revocation and confirms all admitted calls have returned.
    require(read('trace.jsonl', 8 * 1024 * 1024) == trace)
    return {'vmStatus': 'VERIFIED', 'runId': run_id, 'rawCalls': len(calls),
            'files': collected, 'business': business, 'sessionVerified': False}
