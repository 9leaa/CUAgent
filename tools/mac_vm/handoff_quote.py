"""Bounded exact quotation lookup; pure stdlib, no I/O or semantic verdict."""
import hashlib
import unicodedata


def locate(materials, args):
    if (type(args) is not dict or set(args) != {'sourceId', 'quote'}
            or type(args['sourceId']) is not str or not 0 < len(args['sourceId']) <= 80
            or type(args['quote']) is not str):
        raise ValueError('bounded quote arguments required')
    quote = args['quote']
    if not quote.strip() or len(quote.encode('utf-8')) > 2048:
        raise ValueError('bounded nonempty quote required')
    if any(c not in '\n\r\t' and unicodedata.category(c) in {'Cc','Cf','Cs','Zl','Zp'} for c in quote):
        raise ValueError('quote control character denied')
    sources = {f"notes/{n['id']}": n['content'] for n in materials['notes']}
    sources.update(tasksCsv=materials['tasksCsv'], previousReport=materials['previousReport'])
    source_id = args['sourceId']
    if source_id not in sources:
        return dict(status='SOURCE_NOT_FOUND', matches=[], truncated=False)
    original = sources[source_id]
    matches, start = [], 0
    while True:
        at = original.find(quote, start)
        if at < 0:
            break
        if len(matches) == 8:
            return dict(status='AMBIGUOUS', matches=matches, truncated=True)
        matches.append(dict(start=at, end=at+len(quote)))
        start = at+1
    return dict(status='UNIQUE' if len(matches)==1 else 'AMBIGUOUS' if matches else 'NOT_FOUND',
                sourceId=source_id, sourceSha256=hashlib.sha256(original.encode()).hexdigest(),
                matches=matches, truncated=False)
