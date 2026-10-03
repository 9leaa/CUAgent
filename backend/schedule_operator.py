"""Operator-only quota admission. Never obtains quota, clears a stop, or creates tasks."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import fcntl
import json
import math
import os
from pathlib import Path
import stat
import uuid
from agent.daily_report import dump
from backend.models import utcnow

CREDITS = '62494.0260570000'


def private_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid() or info.st_size > 4096:
            raise ValueError('PRIVATE_BOUNDED_RECORD_REQUIRED')
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError('OBJECT_RECORD_REQUIRED')
    return value


class Operator:
    def __init__(self, root, *, clock=utcnow):
        self.root, self.clock = Path(root).absolute(), clock
        if self.root.resolve(strict=True) != self.root or self.root.stat().st_mode & 0o077:
            raise ValueError('PRIVATE_CANONICAL_ROOT_REQUIRED')
        self.permit = self.root / 'scheduler-permit.json'
        self.stop = self.root / 'scheduler-operator-stop.json'

    @contextmanager
    def lock(self):
        fd = os.open(self.root / 'scheduler-operator.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('PRIVATE_LOCK_REQUIRED')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def replace(self, value):
        # Atomic rename prevents the polling scheduler from seeing partially written JSON.
        temporary = self.root / ('operator-permit-' + uuid.uuid4().hex + '.json')
        dump(temporary, value)
        os.replace(temporary, self.permit)

    def receipt(self, action, identity, result, **details):
        value = dict(action=action, scheduleId=identity, result=result,
                     observedAt=self.clock().isoformat(), **details)
        path = self.root / ('operator-receipt-' + uuid.uuid4().hex + '.json')
        dump(path, value)
        return dict(value, receipt=str(path))

    def grant(self, identity, quota_path, load_plan):
        with self.lock():
            if os.path.lexists(self.stop):
                return self.receipt('grant', identity, 'STOP_LATCHED')
            quota = private_json(quota_path)
            now = self.clock()
            try:
                due, checked, expires = (datetime.fromisoformat(quota[k]) for k in ('dueAt', 'checkedAt', 'expiresAt'))
                remaining = quota['remainingPercent']
                valid = (type(quota['version']) is int and quota['version'] == 1 and quota['scheduleId'] == identity
                    and all(t.tzinfo is not None for t in (due, checked, expires, now))
                    and checked <= now < expires <= checked + timedelta(minutes=5)
                    and type(remaining) in (int, float) and math.isfinite(remaining) and 0 <= remaining <= 100
                    and type(quota['ordinaryUsageAllowed']) is bool
                    and isinstance(quota['creditsBalance'], str)
                    and type(quota['resetCardsUsed']) is int and quota['resetCardsUsed'] >= 0)
            except (ValueError, TypeError, KeyError):
                valid = False
            if not valid:
                return self.receipt('grant', identity, 'INVALID_ATTESTATION')
            if remaining < 40 or not quota['ordinaryUsageAllowed'] or quota['creditsBalance'] != CREDITS or quota['resetCardsUsed'] != 0:
                stop = dict(stoppedAt=now.isoformat(), scheduleId=identity, reason='QUOTA_POLICY_STOP')
                dump(self.stop, stop)
                # This stop is global for this single-user run. Existing submitted work is separate.
                self.replace(dict(quota, ordinaryUsageAllowed=False, revocationReason='QUOTA_POLICY_STOP'))
                return self.receipt('grant', identity, 'QUOTA_POLICY_STOP')
            plan = load_plan(identity)  # Re-read while holding the operator lock; never cache between commands.
            if (plan['id'] != identity or plan['status'] != 'ACTIVE' or
                datetime.fromisoformat(plan['next_at']) != due or not due <= now < due + timedelta(minutes=10) or
                any(datetime.fromisoformat(item['due_at']) == due for item in plan['items'])):
                return self.receipt('grant', identity, 'NOT_AN_UNCLAIMED_DUE_OCCURRENCE')
            if os.path.lexists(self.permit):
                existing = private_json(self.permit)
                if existing.get('ordinaryUsageAllowed') is True and datetime.fromisoformat(existing['expiresAt']) > now:
                    return self.receipt('grant', identity, 'LIVE_PERMIT_EXISTS')
            # Keep only documented permission fields; never forward arbitrary account metadata.
            permission = {k: quota[k] for k in ('version', 'scheduleId', 'dueAt', 'checkedAt', 'expiresAt',
                'ordinaryUsageAllowed', 'remainingPercent', 'creditsBalance', 'resetCardsUsed')}
            if not checked <= self.clock() < min(expires, due + timedelta(minutes=10)):
                return self.receipt('grant', identity, 'ATTESTATION_EXPIRED_DURING_CHECK')
            intent = self.receipt('grant', identity, 'INTENT', permission=permission)
            self.replace(permission)
            return self.receipt('grant', identity, 'GRANTED', intentReceipt=intent['receipt'], dueAt=quota['dueAt'])

    def revoke(self, identity):
        with self.lock():
            if not os.path.lexists(self.permit):
                return self.receipt('revoke', identity, 'NO_PERMIT')
            old = private_json(self.permit)
            if old.get('scheduleId') != identity:
                return self.receipt('revoke', identity, 'OTHER_SCHEDULE_PERMIT')
            self.replace(dict(old, ordinaryUsageAllowed=False, revokedAt=self.clock().isoformat(),
                              revocationReason='OPERATOR_REVOKED'))
            return self.receipt('revoke', identity, 'REVOKED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['grant', 'revoke'])
    parser.add_argument('--schedule', type=uuid.UUID, required=True)
    parser.add_argument('--quota', type=Path)
    args = parser.parse_args()
    if args.command == 'grant' and not args.quota:
        parser.error('grant requires --quota from a fresh account check; this tool cannot query the account')
    from backend.config import Settings
    from backend.db import database
    from backend.manage import load_env
    from backend.schedule_runtime import runtime_service
    from backend.service import TaskService
    os.environ.update(load_env())
    settings = Settings.from_env()
    operator = Operator(settings.root)
    if args.command == 'revoke':
        result = operator.revoke(str(args.schedule))
    else:
        _, sessions = database(settings.database_url)
        service = runtime_service(TaskService(sessions, settings))
        result = operator.grant(str(args.schedule), args.quota, service.view)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
