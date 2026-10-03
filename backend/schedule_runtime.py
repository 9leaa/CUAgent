"""Fixed local collectors and operator-recorded, occurrence-bound quota admission."""
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import stat
import subprocess
from zoneinfo import ZoneInfo
from backend.schedules import DAY, ScheduleService
from backend.workflow_sources import PROJECT, collect_operations, project_snapshot


class QuotaPermit:
    """Developer-owned attestation from a fresh account check, not an account API."""
    def __init__(self, path):
        self.path = Path(path).absolute()

    def __call__(self, schedule_id, due_at, now):
        try:
            if self.path.parent.resolve() != self.path.parent or self.path.parent.stat().st_mode & 0o077:
                return False
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd) as file:
                info = os.fstat(file.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid() or info.st_size > 4096:
                    return False
                value = json.loads(file.read(4097))
            checked = datetime.fromisoformat(value['checkedAt'])
            expires = datetime.fromisoformat(value['expiresAt'])
            due = datetime.fromisoformat(value['dueAt'])
            remaining = value['remainingPercent']
            return (value.get('version') == 1 and value.get('scheduleId') == schedule_id and due == due_at
                    and all(d.tzinfo is not None for d in (checked, expires, due, now))
                    and checked <= now < expires <= checked + timedelta(minutes=5)
                    and value.get('ordinaryUsageAllowed') is True
                    and type(remaining) in (int, float) and math.isfinite(remaining) and 5 < remaining <= 100
                    and value.get('creditsBalance') == '62494.0260570000'
                    and type(value.get('resetCardsUsed')) is int and value['resetCardsUsed'] == 0)
        except (OSError, ValueError, KeyError, TypeError):
            return False


class WorkflowCollector:
    def __init__(self, sessions):
        self.sessions = sessions

    def __call__(self, ticket):
        config, due = ticket['config'], ticket['dueAt']
        if config['branch'] not in ('harness-migration', 'p5-personal-workflows'):
            raise ValueError('UNAPPROVED_BRANCH')
        end_commit = subprocess.check_output(['git', 'rev-parse', '--verify',
            'refs/heads/' + config['branch']], cwd=PROJECT, timeout=20, text=True).strip()
        day = due.astimezone(ZoneInfo(config['timezone'])).date().isoformat()
        project = project_snapshot(ticket['lastCommit'], end_commit, day)
        operations = collect_operations(self.sessions, due - DAY, due, day)
        return [project, operations]


def runtime_service(task_service):
    return ScheduleService(task_service, collect=WorkflowCollector(task_service.sessions),
                           permitted=QuotaPermit(task_service.settings.root / 'scheduler-permit.json'))
