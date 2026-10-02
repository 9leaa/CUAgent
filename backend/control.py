"""Cross-process, monotonic execution control outside the model workspace."""
import fcntl
import json
import os
from pathlib import Path
import tempfile


def write_control(path, *, run_id, epoch, owner, expires_at, stopped=False):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.stat().st_mode & 0o077 or path.is_symlink():
        raise ValueError('unsafe control location')
    with (path.parent / (path.name + '.lock')).open('a') as lock:
        os.chmod(lock.name, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            old = json.loads(path.read_text())
            if old['runId'] != run_id or old['epoch'] > epoch:
                raise ValueError('stale execution owner')
            if old['epoch'] == epoch:
                if old['owner'] != owner:
                    raise ValueError('execution owner conflict')
                stopped = stopped or old['stopped']
        value = {'version': 1, 'runId': run_id, 'epoch': epoch, 'owner': owner,
                 'expiresAt': int(expires_at), 'stopped': bool(stopped)}
        fd, temporary = tempfile.mkstemp(prefix='.control-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w') as output:
                json.dump(value, output)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return value
