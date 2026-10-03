from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock
import pytest
from backend.schedule_operator import Operator, CREDITS, private_json
from backend.schedule_runtime import QuotaPermit

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)


def setup(tmp_path, **changes):
    quota = dict(version=1, scheduleId='plan', dueAt=NOW.isoformat(), checkedAt=NOW.isoformat(),
        expiresAt=(NOW+timedelta(minutes=5)).isoformat(), ordinaryUsageAllowed=True, remainingPercent=91,
        creditsBalance=CREDITS, resetCardsUsed=0)
    quota.update(changes)
    path = tmp_path / 'quota.json'; path.write_text(json.dumps(quota)); path.chmod(0o600)
    plan = dict(id='plan', status='ACTIVE', next_at=NOW.isoformat(), items=[])
    return Operator(tmp_path, clock=lambda: NOW), path, Mock(return_value=plan)


def test_grant_atomic_replace_old_revoked_permit_and_revoke(tmp_path):
    operator, quota, loader = setup(tmp_path)
    operator.replace(dict(private_json(quota), ordinaryUsageAllowed=False, scheduleId='old'))
    result = operator.grant('plan', quota, loader)
    assert result['result'] == 'GRANTED'
    assert QuotaPermit(operator.permit)('plan', NOW, NOW)
    assert operator.permit.stat().st_mode & 0o077 == 0
    assert operator.grant('plan', quota, loader)['result'] == 'LIVE_PERMIT_EXISTS'
    assert operator.revoke('other')['result'] == 'OTHER_SCHEDULE_PERMIT'
    assert QuotaPermit(operator.permit)('plan', NOW, NOW)
    assert operator.revoke('plan')['result'] == 'REVOKED'
    assert not QuotaPermit(operator.permit)('plan', NOW, NOW)
    assert operator.revoke('plan')['result'] == 'REVOKED'
    assert len(list(tmp_path.glob('operator-receipt-*.json'))) == 6


@pytest.mark.parametrize('change', [dict(remainingPercent=30), dict(remainingPercent=0),
    dict(ordinaryUsageAllowed=False), dict(creditsBalance='62493'), dict(resetCardsUsed=1)])
def test_budget_stop_persists_across_restart_and_natural_reset(tmp_path, change):
    operator, quota, loader = setup(tmp_path, **change)
    assert operator.grant('plan', quota, loader)['result'] == 'QUOTA_POLICY_STOP'
    loader.assert_not_called()
    operator, quota, loader = setup(tmp_path, remainingPercent=100)
    assert operator.grant('plan', quota, loader)['result'] == 'STOP_LATCHED'
    assert private_json(operator.permit)['ordinaryUsageAllowed'] is False
    loader.assert_not_called()


@pytest.mark.parametrize('change', [dict(version=True), dict(remainingPercent=True),
    dict(remainingPercent=float('nan')), dict(expiresAt=(NOW+timedelta(minutes=6)).isoformat()),
    dict(checkedAt=(NOW+timedelta(seconds=1)).isoformat()), dict(dueAt='2026-10-03T00:00:00'),
    dict(scheduleId='other'), dict(resetCardsUsed=False)])
def test_invalid_attestation_cannot_grant_or_create_stop(tmp_path, change):
    operator, quota, loader = setup(tmp_path, **change)
    assert operator.grant('plan', quota, loader)['result'] == 'INVALID_ATTESTATION'
    assert not operator.permit.exists() and not operator.stop.exists()
    loader.assert_not_called()


@pytest.mark.parametrize('change', [dict(status='PAUSED'), dict(next_at=(NOW+timedelta(days=1)).isoformat()),
    dict(items=[dict(due_at=NOW.isoformat())])])
def test_plan_must_be_active_due_and_unclaimed(tmp_path, change):
    operator, quota, loader = setup(tmp_path)
    loader.return_value.update(change)
    assert operator.grant('plan', quota, loader)['result'] == 'NOT_AN_UNCLAIMED_DUE_OCCURRENCE'
    assert not operator.permit.exists()


def test_symlinks_public_files_and_concurrent_operator_rejected(tmp_path):
    operator, quota, loader = setup(tmp_path)
    link = tmp_path/'link.json'; link.symlink_to(quota)
    with pytest.raises(OSError): operator.grant('plan', link, loader)
    quota.chmod(0o644)
    with pytest.raises(ValueError): operator.grant('plan', quota, loader)
    quota.chmod(0o600)
    with operator.lock():
        with pytest.raises(BlockingIOError): Operator(tmp_path, clock=lambda: NOW).grant('plan', quota, loader)
    assert not operator.permit.exists()


def test_source_error_never_installs_permission(tmp_path):
    operator, quota, loader = setup(tmp_path)
    loader.side_effect = RuntimeError('database unavailable')
    with pytest.raises(RuntimeError): operator.grant('plan', quota, loader)
    assert not operator.permit.exists()


def test_quota_expiring_during_plan_read_is_not_installed(tmp_path):
    operator, quota, loader = setup(tmp_path)
    def slow_plan(identity):
        operator.clock = lambda: NOW+timedelta(minutes=5)
        return loader.return_value
    assert operator.grant('plan', quota, slow_plan)['result'] == 'ATTESTATION_EXPIRED_DURING_CHECK'
    assert not operator.permit.exists()
