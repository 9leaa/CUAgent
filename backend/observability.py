import json


def session_usage(path):
    """Count even cancelled/failed turns; do not infer currency from total tokens."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    messages = [r['data'] for r in rows if r['type'] == 'assistant/message']
    fields = ['inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'totalTokens']
    available = bool(messages) and all(isinstance(m.get('usage'), dict) and
        all(type(m['usage'].get(k)) is int and m['usage'][k] >= 0 for k in fields) for m in messages)
    routes = []
    for row in rows:
        if row['type'] == 'request/header':
            config = row['data']['header']['config']
            route = {k: config.get(k) for k in ('provider', 'model', 'reasoningEffort')}
            if route not in routes:
                routes.append(route)
    return {'available': available, **{k: sum(m['usage'][k] for m in messages) if available else None for k in fields},
            'models': routes, 'monetaryCost': None}
