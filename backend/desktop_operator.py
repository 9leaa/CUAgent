"""Task-bound, one-shot desktop Worker. Requires an already approved cutover."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import uuid

from sqlalchemy import select, func

from backend.db import database
from backend.desktop_adapter import DesktopAdapterSettings, DesktopTaskAdapter
from backend.desktop_collect import GUEST_PYTHON, private_path, run_bounded, save_exclusive
from backend.desktop_service import baseline, load_profile, read_private
from backend.desktop_ssh import create_ssh_wrapper
from backend.desktop_worker import DesktopWorker
from backend.models import Attempt, Resource, Schedule, Task
from backend.schedule_operator import CREDITS
from backend.service import TaskService


def record(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('DUPLICATE_OPERATOR_FIELD')
            result[key] = value
        return result
    value = json.loads(read_private(path), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError('OPERATOR_OBJECT_REQUIRED')
    return value


class QuotaGate:
    def __init__(self, root, profile_path, task_id, quota_path, *, clock=None):
        self.root, self.profile_path = Path(root), Path(profile_path)
        info = self.root.stat()
        if (self.root.resolve(strict=True) != self.root or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid() or info.st_mode & 0o022):
            raise ValueError('OWNED_OPERATOR_ROOT_REQUIRED')
        self.task_id, self.quota_path = task_id, Path(quota_path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.stop = self.root / 'desktop-operator-stop.json'
        self.profile_sha = hashlib.sha256(read_private(profile_path).encode()).hexdigest()
        self.quota_sha = hashlib.sha256(read_private(quota_path).encode()).hexdigest()

    def check(self):
        if os.path.lexists(self.stop):
            raise RuntimeError('DESKTOP_QUOTA_STOP_LATCHED')
        if (hashlib.sha256(read_private(self.profile_path).encode()).hexdigest() != self.profile_sha
                or hashlib.sha256(read_private(self.quota_path).encode()).hexdigest() != self.quota_sha):
            raise ValueError('OPERATOR_RECORD_CHANGED')
        value = record(self.quota_path)
        fields = {'version', 'taskId', 'profileSha256', 'source', 'checkedAt', 'expiresAt',
                  'remainingPercent', 'ordinaryUsageAllowed', 'creditsBalance', 'resetCardsUsed'}
        if (set(value) != fields or type(value['version']) is not int or value['version'] != 1
                or value['taskId'] != self.task_id or value['profileSha256'] != self.profile_sha
                or value['source'] != 'Codex get_usage_limits'):
            raise ValueError('INVALID_TASK_QUOTA_BINDING')
        checked, expires = (datetime.fromisoformat(value[key]) for key in ('checkedAt', 'expiresAt'))
        remaining = value['remainingPercent']
        if (checked.tzinfo is None or expires.tzinfo is None
                or not checked <= self.clock() < expires <= checked + timedelta(minutes=5)
                or type(remaining) not in (int, float) or not math.isfinite(remaining) or not 0 <= remaining <= 100
                or type(value['ordinaryUsageAllowed']) is not bool
                or not isinstance(value['creditsBalance'], str)
                or type(value['resetCardsUsed']) is not int or value['resetCardsUsed'] < 0):
            raise ValueError('INVALID_OR_EXPIRED_QUOTA')
        if (remaining < 40 or not value['ordinaryUsageAllowed']
                or value['creditsBalance'] != CREDITS or value['resetCardsUsed'] != 0):
            save_exclusive(self.stop, json.dumps({'taskId': self.task_id, 'reason': 'QUOTA_POLICY_STOP',
                'quotaSha256': self.quota_sha, 'observedAt': self.clock().isoformat()}).encode())
            raise RuntimeError('DESKTOP_QUOTA_POLICY_STOP')
        return True


def adapter_settings(path, profile):
    data = record(path)
    fields = {'version', 'node', 'officialHome', 'buildTools', 'knownHosts', 'askpass',
              'guestCommit', 'guestManifestSha256', 'tunnelPort'}
    if (set(data) != fields or type(data['version']) is not int or data['version'] != 1
            or not re.fullmatch('[0-9a-f]{40}', data['guestCommit'])
            or not re.fullmatch('[0-9a-f]{64}', data['guestManifestSha256'])
            or type(data['tunnelPort']) is not int or not 19000 <= data['tunnelPort'] <= 19999):
        raise ValueError('INVALID_EXECUTION_CONFIGURATION')
    node = Path(data['node'])
    if not node.is_absolute() or node.resolve(strict=True) != node or not node.is_file() or not os.access(node, os.X_OK):
        raise ValueError('CANONICAL_NODE_EXECUTABLE_REQUIRED')
    home = private_path(data['officialHome'], directory=True)
    build = Path(data['buildTools']).absolute()
    info = build.stat()
    if (build.resolve(strict=True) != build or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022):
        raise ValueError('OWNED_NONWRITABLE_BUILD_DIRECTORY_REQUIRED')
    return DesktopAdapterSettings(node, home, profile.settings.cookie_file, build, profile.settings.base_tasks,
        Path(data['knownHosts']), Path(data['askpass']), data['guestCommit'], data['guestManifestSha256'],
        data['tunnelPort'], True)


class LiveGate:
    def __init__(self, profile, quota, wrapper):
        self.profile, self.quota, self.wrapper = profile, quota, wrapper
        self.baseline_sha = hashlib.sha256(read_private(profile.baseline_env).encode()).hexdigest()

    def __call__(self, task=None):
        self.quota.check()
        if hashlib.sha256(read_private(self.profile.baseline_env).encode()).hexdigest() != self.baseline_sha:
            raise ValueError('BASELINE_CONFIGURATION_CHANGED')
        if task is not None and task.id != self.quota.task_id:
            raise ValueError('OTHER_TASK_NOT_AUTHORIZED')
        old = baseline(self.profile.baseline_env)
        if os.path.lexists(Path(old['CUAGENT_BACKEND_ROOT']) / 'scheduler-operator-stop.json'):
            raise RuntimeError('BASELINE_QUOTA_STOP_LATCHED')
        engine, sessions = database(old['CUAGENT_DATABASE_URL'])
        try:
            with sessions() as db:
                now = db.scalar(select(func.clock_timestamp()))
                busy = db.scalar(select(Task.id).where(Task.status.in_(
                    ['QUEUED', 'WAITING_RELEASE', 'RUNNING', 'STOP_REQUESTED'])).limit(1))
                owner = db.scalar(select(Resource.owner).where(Resource.name == 'desktop'))
                due = db.scalar(select(Schedule.id).where(Schedule.status == 'ACTIVE',
                    Schedule.next_at <= now + timedelta(minutes=30)).limit(1))
                if busy or owner or due:
                    raise RuntimeError('BASELINE_NOT_IDLE_OR_SCHEDULE_TOO_CLOSE')
        finally:
            engine.dispose()
        processes = run_bounded(['/bin/ps', '-axo', 'command='], b'', limit=1048576, timeout=5).decode()
        if any(re.search(r'(?:^|\s)-m\s+backend\.worker(?:\s|$)', row) for row in processes.splitlines()):
            raise RuntimeError('BASELINE_WORKER_MUST_BE_STOPPED_IN_APPROVED_WINDOW')
        code = ('import json,plistlib,subprocess; '
                'd=plistlib.loads(subprocess.check_output(["/usr/sbin/ioreg","-n","Root","-d1","-a"])); '
                'u=subprocess.check_output(["/usr/bin/id","-un"],text=True).strip(); '
                'm=subprocess.check_output(["/usr/sbin/sysctl","-n","hw.model"],text=True).strip(); '
                'ok=not d.get("IOConsoleLocked",False) and any(x.get("kCGSSessionUserNameKey")=="mvpagent" '
                'and x.get("kCGSSessionOnConsoleKey") is True and not x.get("CGSSessionScreenIsLocked",False) '
                'for x in d.get("IOConsoleUsers",[])); '
                'print(json.dumps({"username":u,"model":m,"unlocked":ok}))')
        state = json.loads(run_bounded([str(self.wrapper), '-F', '/dev/null',
            shlex.join([GUEST_PYTHON, '-c', code])], b'', limit=4096, timeout=15))
        if state != {'username': 'mvpagent', 'model': 'VirtualMac2,1', 'unlocked': True}:
            raise RuntimeError('APPROVED_VM_NOT_READY')
        self.quota.check()  # Read-only preflight time cannot extend admission.
        return True


def worker_once(*, profile_path, execution_path, quota_path, task_id, cutover_approved=False):
    if cutover_approved is not True or str(uuid.UUID(task_id)) != task_id:
        raise ValueError('EXPLICIT_CUTOVER_AND_CANONICAL_TASK_REQUIRED')
    profile = load_profile(profile_path)
    root = Path(profile_path).absolute().parent
    old = baseline(profile.baseline_env)
    shared_root = Path(old['CUAGENT_BACKEND_ROOT']).resolve(strict=True).parent
    quota = QuotaGate(shared_root, profile_path, task_id, quota_path)
    quota.check()
    settings = adapter_settings(execution_path, profile)
    engine, sessions = database(profile.settings.database_url)
    service = TaskService(sessions, profile.settings)
    admission = root / ('admission-' + uuid.uuid4().hex)
    admission.mkdir(mode=0o700)
    wrapper = create_ssh_wrapper(root=admission, known_hosts=settings.known_hosts, askpass=settings.askpass)
    gate = LiveGate(profile, quota, wrapper)
    adapter = DesktopTaskAdapter(service, settings, execution_gate=gate)
    # Derived from the protected baseline, never from task text or a selectable alternate lock.
    worker = DesktopWorker(service, adapter, shared_lock=shared_root / 'desktop-worker.lock')
    def before_claim():
        with sessions() as db:
            task = db.get(Task, task_id)
            attempted = db.scalar(select(Attempt.id).where(Attempt.task_id == task_id).limit(1))
            if (task is None or task.status != 'QUEUED' or task.payload.get('kind') != 'desktop-textedit'
                    or attempted is not None or task.session_id or task.calls or task.run_dir):
                raise ValueError('ONLY_ORIGINAL_UNATTEMPTED_QUEUED_TASK_ALLOWED')
        gate()
        save_exclusive(root / ('desktop-launch-' + task_id + '.json'), json.dumps({
            'taskId': task_id, 'profileSha256': quota.profile_sha, 'quotaSha256': quota.quota_sha,
            'admission': str(admission), 'action': 'SINGLE_CLAIM_INTENT'}).encode())
        return True
    try:
        outcome = worker.run_once(task_id=task_id, before_claim=before_claim)
        receipt = {'result': 'EXECUTION_RECORDED' if outcome else 'NOT_CLAIMED',
                   'taskId': task_id, 'outcome': outcome}
        save_exclusive(admission / 'outcome.json', json.dumps(receipt).encode())
        return receipt
    except Exception as error:
        save_exclusive(admission / 'refusal.json', json.dumps({'taskId': task_id,
            'result': 'REFUSED_OR_UNCONFIRMED', 'errorType': type(error).__name__}).encode())
        raise
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['worker-once'])
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--execution', type=Path, required=True)
    parser.add_argument('--quota', type=Path, required=True)
    parser.add_argument('--task', type=uuid.UUID, required=True)
    parser.add_argument('--cutover-approved', action='store_true')
    args = parser.parse_args()
    try:
        result = worker_once(profile_path=args.profile, execution_path=args.execution, quota_path=args.quota,
                             task_id=str(args.task), cutover_approved=args.cutover_approved)
        print(json.dumps(result))
    except Exception:
        print(json.dumps({'result': 'REFUSED_OR_UNCONFIRMED',
                          'action': 'Inspect original task, admission and quarantine; never replay blindly.'}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
