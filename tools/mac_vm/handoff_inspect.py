"""Trusted local read-only inspection command; never controls a VM or model."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from handoff_evidence import inspect_handoff_evidence, strict_json, require
from handoff_exchanges import match_handoff_exchanges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--draft-input-mode', choices=('literal-text','checked-draft-v1'), default='literal-text')
    args = parser.parse_args()
    payload = sys.stdin.buffer.read(512 * 1024 + 1)
    require(len(payload) <= 512 * 1024)
    value = strict_json(payload)
    require(type(value) is dict and set(value) == {'binding', 'materialsBase64', 'expectedBase64'})
    materials = base64.b64decode(value['materialsBase64'], validate=True)
    expected = base64.b64decode(value['expectedBase64'], validate=True)
    path = Path(args.session).absolute()
    require(path.resolve(strict=True) == path and path.name == 'session.jsonl'
            and path.parent.name == value['binding']['runId'])
    def read(target=path, limit=64 * 1024 * 1024):
        require(target.resolve(strict=True) == target)
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
                    and info.st_nlink == 1 and 0 < info.st_size <= limit)
            raw = stream.read(info.st_size + 1)
            require(len(raw) == info.st_size)
            return raw
    raw = read()
    guest = inspect_handoff_evidence(args.directory, binding=value['binding'], materials=materials, expected=expected,
                                    draft_input_mode=args.draft_input_mode)
    trace_raw = read(Path(args.directory).absolute() / 'trace.jsonl', 8 * 1024 * 1024)
    require(hashlib.sha256(trace_raw).hexdigest() == guest['files']['trace.jsonl']['sha256'])
    trace = [strict_json(line) for line in trace_raw.splitlines()]
    session_id = None
    if any(r.get('tool') == 'check_draft' for r in trace):
        session_raw = read(Path(args.directory).absolute() / 'handoff-session-binding.json', 4096)
        require(hashlib.sha256(session_raw).hexdigest() == guest['files']['handoff-session-binding.json']['sha256'])
        session_id = strict_json(session_raw)['sessionId']
    exchanges = match_handoff_exchanges([strict_json(line) for line in raw.splitlines()], trace,
        run_id=value['binding']['runId'], materials=materials, expected=expected, session_id=session_id,
        draft_input_mode=args.draft_input_mode)
    require(read() == raw)
    print(json.dumps(dict(guest=guest, exchanges=exchanges, sessionSha256=hashlib.sha256(raw).hexdigest())))


if __name__ == '__main__':
    try: main()
    except Exception:
        print('HANDOFF_INSPECTION_UNVERIFIED', file=sys.stderr)
        raise SystemExit(1)
