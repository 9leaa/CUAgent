"""Read original session usage; absence is unknown, never a free execution."""
import hashlib
import json
import os
import stat
from backend.desktop_collect import private_path

FIELDS = ('inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'totalTokens')


def desktop_usage(root, session_id):
    unknown = {'available': False, **dict.fromkeys(FIELDS), 'models': [], 'monetaryCost': None}
    try:
        root = private_path(root, directory=True)
        def read(name, limit):
            path = private_path(root / name, directory=False)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise ValueError('private file required')
                raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('bounded evidence required')
            return raw
        binding = json.loads(read('desktop-session-binding.json', 32768))
        if binding['sessionId'] != session_id or binding['runId'] != root.name or binding['cwd'] != str(root / 'workspace'):
            return unknown
        raw = read('session.jsonl', 64 * 1024 * 1024)
        rows = [json.loads(line) for line in raw.splitlines()]
        if rows and rows[0].get('type') == 'session':
            header = rows.pop(0)
            if (header.get('version') != 4 or header.get('id') != session_id
                    or header.get('cwd') != binding['cwd'] or 'seq' in header):
                return unknown
        if (not rows or any(type(r.get('seq')) is not int for r in rows)
                or [r['seq'] for r in rows] != sorted({r['seq'] for r in rows})):
            return unknown
        messages = [r['data'] for r in rows if r['type'] == 'assistant/message']
        ends = [r for r in rows if r['type'] == 'turn/end']
        # Partial archives may omit later consumption. Report only a terminal
        # snapshot; cancelled/failed terminal turns still count their usage.
        if len(ends) != 1 or any(r['seq'] > ends[0]['seq'] for r in rows if r['type'] == 'assistant/message'):
            return unknown
        if not messages or not all(isinstance(m.get('usage'), dict) and
            all(type(m['usage'].get(k)) is int and m['usage'][k] >= 0 for k in FIELDS) and
            m['usage']['totalTokens'] == sum(m['usage'][k] for k in FIELDS[:-1]) for m in messages):
            return unknown
        routes = []
        for row in rows:
            if row['type'] == 'request/header':
                config = row['data']['header']['config']
                route = {k: config[k] for k in ('provider', 'model', 'reasoningEffort')}
                if not all(isinstance(v, str) and v for v in route.values()):
                    return unknown
                if route not in routes:
                    routes.append(route)
        if not routes:
            return unknown
        return {'available': True, **{k: sum(m['usage'][k] for m in messages) for k in FIELDS},
                'models': routes, 'monetaryCost': None, 'sessionSha256': hashlib.sha256(raw).hexdigest()}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return unknown
