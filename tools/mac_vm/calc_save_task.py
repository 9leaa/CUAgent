"""Opt-in save-dialog entry on the original input ledger; no file writer."""
import json
import os
from pathlib import Path
import stat

from calc_input_task import CalcInputTask
from calc_save import plan_open_save, workbook_destination
from calc_selection import _save
from driver_smoke import StopRun


def inspect_unused_destination(destination):
    """Read-only admission, not a reservation; must repeat before final Save."""
    path=Path(destination)
    if not path.is_absolute() or str(path)!=destination or path.parent!=Path('/Users/mvpagent/Documents'):
        raise ValueError('fixed guest Documents destination required')
    return _inspect_unused_path(path)


def _inspect_unused_path(path):
    # Kept separately for real temporary-filesystem tests; no mkdir or write.
    for parent in reversed(path.parents):
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise ValueError('canonical destination ancestry required')
    parent=path.parent.lstat()
    if parent.st_uid!=os.getuid() or parent.st_mode & 0o022:
        raise ValueError('owned non-shared destination directory required')
    if os.path.lexists(path):raise ValueError('destination already exists; no overwrite')
    return dict(device=parent.st_dev,inode=parent.st_ino,uid=parent.st_uid)


class CalcSaveTask(CalcInputTask):
    def __init__(self,*args,save_approved=False,destination=None,toolbar_region=None,
                 destination_check=inspect_unused_destination,**kwargs):
        if save_approved is not True or not args or destination!=workbook_destination(Path(args[0]).name):
            raise ValueError('explicit original save binding required')
        from calc_targeting import _number
        r=toolbar_region
        if not isinstance(r,(list,tuple)) or len(r)!=4 or not all(_number(v) for v in r) or not 0<=r[0]<r[2] or not 0<=r[1]<r[3]:
            raise ValueError('reviewed Save toolbar region required')
        self.destination=destination;self.toolbar_region=tuple(r)
        self.destination_check=destination_check
        super().__init__(*args,**kwargs)
        try:
            self.destination_identity=destination_check(destination)
            binding=dict(destination=destination,toolbarRegion=list(r),parentIdentity=self.destination_identity)
            path=self.directory/'save-binding.json'
            if path.exists() or path.is_symlink():
                if path.is_symlink() or json.loads(path.read_bytes())!=binding:raise ValueError('original save binding changed')
            else:_save(path,json.dumps(binding).encode())
        except Exception:
            self.close();raise

    def open_save(self, *, snapshot_id, name_box_index, point=None):
        with self.lock:
            try:
                if (self.phase!='COMMIT_CONFIRMED' or self.stopped.is_set() or self.uncertain
                        or self.lock_fd is None or not self.snapshot or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Confirmed current commit required before save')
                self.environment();self.lease.check();self.identity(self.pid)
                if self.used>16:raise StopRun('BLOCKED','Reserve at least fourteen raw calls for save/reopen/verification')
                if self.destination_check(self.destination)!=self.destination_identity:
                    raise StopRun('BLOCKED','Destination parent changed')
                plan=plan_open_save(self.snapshot,**self._context(),grid=self.grid,
                    previous_snapshot_id=self.before_commit,name_box_index=name_box_index,
                    approved=True,overwrite_disposable=True,text=self.input_text,kind=self.input_kind,
                    approved_text=self.input_text,approved_kind=self.input_kind,formula_region=self.formula_region,
                    run_id=self.run_id,destination=self.destination,save_approved=True,toolbar_region=self.toolbar_region,point=point)
                _save(self.directory/'save-open-attempt.json',json.dumps(plan).encode())
                self.record(dict(event='save_open_intent',plan=plan,used=self.used))
                self.phase='SAVE_OPEN_ATTEMPTED';self.snapshot=None
                delivery={'delivery_mode':'foreground'} if plan['route']=='screenshot' else {}
                self._call('click',dict(pid=self.pid,window_id=self.window,session=self.run_id,**plan['target'],**delivery))
                result=self.observe()
                if result['state']['snapshot_id']==snapshot_id:raise ValueError('new save dialog observation required')
                self.phase='AWAITING_SAVE_DIALOG'
                return dict(result,status='SAVE_DIALOG_ATTEMPT_OBSERVED',saved=False,savePermitted=False,
                            businessStatus='UNVERIFIED')
            except Exception:
                self.stop();raise
