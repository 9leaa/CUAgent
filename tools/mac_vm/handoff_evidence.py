"""Bounded, read-only P7 evidence collection, independent of task execution.

Caller must revoke execution, confirm zero in-flight calls, and collect through
the trusted channel. Hashes cannot authenticate a malicious machine owner.
PNG signatures/hashes are not an independent interpretation of image content.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from handoff_trace import verify_handoff_trace


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_FILES_UNVERIFIED')


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    def constant(_):
        raise ValueError('HANDOFF_FILES_UNVERIFIED')

    return json.loads(raw.decode('utf8'), object_pairs_hook=pairs, parse_constant=constant)


def same_json(left, right):
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return encode(left) == encode(right)


def inspect_handoff_evidence(directory, *, binding, materials, expected, draft_input_mode='literal-text'):
    require(draft_input_mode in ('literal-text', 'checked-draft-v1'))
    checked_input = draft_input_mode == 'checked-draft-v1'
    require(type(binding) is dict and set(binding) == {'version', 'runId', 'owner', 'epoch'})
    require(type(binding['version']) is int and binding['version'] == 1
            and type(binding['epoch']) is int and binding['epoch'] > 0
            and type(binding['owner']) is str and bool(binding['owner'])
            and type(binding['runId']) is str)
    require(type(materials) is bytes and 0 < len(materials) <= 256 * 1024)
    require(type(expected) is bytes and 0 < len(expected) <= 4096)
    run = binding['runId']
    root = Path(directory).absolute()
    require(root.resolve(strict=True) == root and root.name == run)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        root_info = os.fstat(root_fd)
        require(root_info.st_uid == os.getuid() and not root_info.st_mode & 0o077)
        collected, contents, limits, signatures, private_files = {}, {}, {}, {}, set()
        total = 0

        def read(name, limit, *, private=False, recheck=False):
            nonlocal total
            parts = name.split('/')
            require(all(part and part not in ('.', '..') for part in parts))
            parent = os.dup(root_fd)
            try:
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent); parent = child
                    info = os.fstat(parent)
                    require(info.st_uid == os.getuid() and not info.st_mode & 0o077)
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(fd, 'rb') as stream:
                    before = os.fstat(stream.fileno())
                    require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                            and before.st_nlink == 1 and 0 < before.st_size <= limit)
                    require(not private or not before.st_mode & 0o077)
                    data = stream.read(limit + 1)
                    after = os.fstat(stream.fileno())
                signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_nlink)
                require(len(data) == before.st_size and signature(before) == signature(after))
                require(signature(after) == signature(os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)))
            finally:
                os.close(parent)
            if recheck:
                require(data == contents[name] and signature(after) == signatures[name])
            else:
                require(name not in contents)
                total += len(data)
                require(total <= 64 * 1024 * 1024)
                contents[name], limits[name] = data, limit
                signatures[name] = signature(after)
                if private: private_files.add(name)
                collected[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            return data

        frozen = read('handoff-input.json', 256 * 1024, private=True)
        require(frozen == materials)
        strict_json(frozen)
        input_sha = hashlib.sha256(materials).hexdigest()
        for name, status in [('handoff-input-intent.json', 'INTENT'), ('handoff-input-receipt.json', 'STORED')]:
            record = strict_json(read(name, 4096, private=True))
            require(type(record) is dict and set(record) == {'status', 'binding', 'inputSha256', 'bytes'})
            require(type(record.get('bytes')) is int and record['bytes'] == len(materials)
                    and record.get('status') == status and record.get('inputSha256') == input_sha)
            require(type(record.get('binding')) is dict and record['binding'] == binding
                    and type(record['binding'].get('version')) is int and type(record['binding'].get('epoch')) is int)
        trace_raw = read('trace.jsonl', 8 * 1024 * 1024, private=True)
        rows = [strict_json(line) for line in trace_raw.splitlines()]
        session_id = None
        if any(r.get('tool') == 'check_draft' for r in rows):
            session = strict_json(read('handoff-session-binding.json', 4096, private=True))
            require(type(session) is dict and set(session) == {'runId', 'sessionId', 'inputSha256'}
                    and session['runId'] == run and session['inputSha256'] == input_sha)
            session_id = session['sessionId']
        if any(r.get('tool') == 'submit_handoff' for r in rows):
            protocol = strict_json(read('handoff-submission-protocol.json', 4096, private=True))
            require(same_json(protocol, dict(version=1, protocol='p7-tool-submit-v1',
                runId=run, sessionId=session_id, inputSha256=input_sha)))
        if checked_input:
            mode = strict_json(read('handoff-input-mode.json', 4096, private=True))
            require(session_id is not None and same_json(mode, dict(version=1, inputMode=draft_input_mode,
                runId=run, sessionId=session_id, inputSha256=input_sha)))
        else:
            require(not os.path.lexists(root / 'handoff-input-mode.json'))
        trace = verify_handoff_trace(rows, run_id=run, materials=materials, expected=expected,
                                     session_id=session_id, draft_input_mode=draft_input_mode)
        intent = strict_json(read('handoff-reopen-intent.json', 4096, private=True))
        marker = next(row for row in rows if row['event'] == 'handoff_reopen_intent')
        require(type(intent) is dict and set(intent) == {'snapshot_id', 'pid', 'window_id', 'sha256', 'element_index', 'element_token'})
        require(type(intent['pid']) is int and type(intent['window_id']) is int
                and intent == {key: marker[key] for key in intent})
        calls = {row['used']: row['call_id'] for row in rows if row['event'] == 'dispatch'}
        results = {row['call_id']: row['value'] for row in rows if row['event'] == 'result'}
        final = None
        for row in rows:
            if row['event'] != 'observation_evidence': continue
            files = row.get('files')
            require(type(files) is dict and set(files) == {'json', 'png'})
            state = results[calls[row['used']]]
            for extension in ('json', 'png'):
                name = 'state-%02d.' % row['used'] + extension
                data = read(name, 8 * 1024 * 1024)
                require(type(files[extension]) is dict and type(files[extension].get('bytes')) is int
                        and files[extension] == collected[name])
                if extension == 'json': require(same_json(strict_json(data), state))
                else: require(data.startswith(b'\x89PNG\r\n\x1a\n'))
            if state['snapshot_id'] == trace['finalSnapshotId']: final = state
        require(final is not None and same_json(strict_json(read('final_state.json', 8 * 1024 * 1024)), final))
        require(read('artifacts/handoff-' + run + '.txt', 4096) == expected)
        require(read('result.txt', 4097) == expected + b'\n')
        # Read all original files a second time, not just the final ledger.
        for name in contents:
            read(name, limits[name], private=name in private_files, recheck=True)
        current = root.stat(follow_symlinks=False)
        require(root.resolve(strict=True) == root and (current.st_dev, current.st_ino) == (root_info.st_dev, root_info.st_ino)
                and current.st_uid == os.getuid() and not current.st_mode & 0o077)
        return {**({'inputMode': draft_input_mode} if checked_input else {}),
                'status': 'VM_EVIDENCE_VERIFIED', 'runId': run, 'binding': dict(binding),
                'rawCalls': trace['rawCalls'], 'files': collected, 'trace': trace,
                'filesVerified': True, 'sessionVerified': False, 'semanticVerified': False}
    finally:
        os.close(root_fd)
