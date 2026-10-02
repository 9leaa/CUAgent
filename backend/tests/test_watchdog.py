from datetime import datetime, timedelta, timezone
import pytest
from backend.watchdog import observe


def test_heartbeat_does_not_extend_business_deadline_and_restart_preserves_it():
    now = datetime(2026, 10, 2, tzinfo=timezone.utc)
    state = observe(None, [1, 5, 5], now=now)
    for seconds in (3, 60, 299):
        state = observe(dict(state), [1, 5, 5], now=now + timedelta(seconds=seconds))
        assert not state['stalled'] and state['lastProgressAt'] == now.isoformat()
    assert observe(dict(state), [1, 5, 5], now=now + timedelta(seconds=300))['stalled']
    moved = observe(state, [1, 6, 5], now=now + timedelta(seconds=301))
    assert not moved['stalled']
    assert observe(moved, [1, 6, 6], now=now + timedelta(seconds=302))['lastProgressAt'] != moved['lastProgressAt']


def test_progress_regression_or_clock_rollback_is_not_progress():
    now = datetime(2026, 10, 2, tzinfo=timezone.utc)
    state = observe(None, [1, 5, 5], now=now)
    with pytest.raises(ValueError, match='REGRESSED'):
        observe(state, [1, 4, 4], now=now)
    with pytest.raises(ValueError, match='CLOCK'):
        observe(state, [1, 5, 5], now=now - timedelta(seconds=1))
    with pytest.raises(ValueError, match='INVALID'):
        observe(None, [True, 0, 0], now=now)
