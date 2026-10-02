"""Business progress, not liveness: serializable deadlines across worker restarts."""
from datetime import datetime, timezone


def observe(previous, marker, *, now=None, idle_seconds=300):
    now = now or datetime.now(timezone.utc)
    if not marker or any(type(value) is not int or value < 0 for value in marker):
        raise ValueError('INVALID_PROGRESS_MARKER')
    prior = previous.get('marker') if previous else None
    if prior is not None and (len(prior) != len(marker) or any(new < old for new, old in zip(marker, prior))):
        raise ValueError('BUSINESS_PROGRESS_REGRESSED')
    if prior != marker:
        at = now
    else:
        at = datetime.fromisoformat(previous['lastProgressAt'])
        if at.tzinfo is None or at > now:
            raise ValueError('PROGRESS_CLOCK_INVALID')
    return {'marker': marker, 'lastProgressAt': at.isoformat(),
            'stalled': (now - at).total_seconds() >= idle_seconds}
