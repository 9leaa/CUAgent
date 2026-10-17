"""Opt-in save-dialog entry on the original input ledger; no file writer."""
import json
import os
from pathlib import Path
import stat
import time

from calc_input_task import CalcInputTask
from calc_save import plan_open_save, workbook_destination, discover_new_panel, panel_inventory
from calc_targeting import _state
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
    RAW_TOOLS = CalcInputTask.RAW_TOOLS | {'list_windows'}

    def __init__(self,*args,save_approved=False,destination=None,toolbar_region=None,
                 destination_check=inspect_unused_destination,**kwargs):
        if save_approved is not True or not args or destination!=workbook_destination(Path(args[0]).name):
            raise ValueError('explicit original save binding required')
        from calc_targeting import _number
        r=toolbar_region
        if not isinstance(r,(list,tuple)) or len(r)!=4 or not all(_number(v) for v in r) or not 0<=r[0]<r[2] or not 0<=r[1]<r[3]:
            raise ValueError('reviewed Save toolbar region required')
        self._panel_read_window=None;self._panel_baseline=None;self.panel_window=None
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

    def validate_raw(self, tool, args):
        if tool=='list_windows' and args!={'pid':self.pid,'include_accessory_windows':True}:
            raise StopRun('BLOCKED','Only original-process accessory discovery permitted')
        if tool=='get_window_state' and self._panel_read_window is not None:
            if (self._permit!=(tool,args) or args!={'pid':self.pid,'window_id':self._panel_read_window,'session':self.run_id}
                    or self.phase not in ('SAVE_OPEN_ATTEMPTED','AWAITING_SAVE_DIALOG')):
                raise StopRun('BLOCKED','Only internally selected panel observation permitted')
            self.identity(self.pid)
            return
        super().validate_raw(tool,args)

    def observe(self):
        if self.phase not in ('SAVE_OPEN_ATTEMPTED','AWAITING_SAVE_DIALOG'):
            return super().observe()
        with self.lock:
            try:
                self.snapshot=None
                windows=self._call('list_windows',{'pid':self.pid,'include_accessory_windows':True})
                panel=discover_new_panel(self._panel_baseline,windows,pid=self.pid,document_window=self.window)
                if self.panel_window is not None and panel['window_id']!=self.panel_window:
                    raise ValueError('bound save panel changed')
                self.panel_window=panel['window_id']
                self._panel_read_window=self.panel_window
                try:
                    state=self._call('get_window_state',dict(pid=self.pid,window_id=self.panel_window,session=self.run_id))
                finally:
                    self._panel_read_window=None
                self.observed_at=time.monotonic()
                _state(state,pid=self.pid,window_id=self.panel_window,title='Save',observed_at=self.observed_at,now=time.monotonic())
                if state['window_bounds']!=panel['bounds']:
                    raise ValueError('panel geometry changed during observation')
                self.record(dict(event='save_panel_observed',documentWindow=self.window,panel=panel,used=self.used,
                                 snapshot_id=state['snapshot_id'],inputPermitted=False,savePermitted=False))
                return self._retain_observation(state)
            except Exception:
                self.stop();raise

    def open_save(self, *, snapshot_id, name_box_index, point=None):
        with self.lock:
            try:
                if (self.phase!='COMMIT_CONFIRMED' or self.stopped.is_set() or self.uncertain
                        or self.lock_fd is None or not self.snapshot or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Confirmed current commit required before save')
                self.environment();self.lease.check();self.identity(self.pid)
                if self.used>14:raise StopRun('BLOCKED','Reserve at least sixteen raw calls for discovery/save/reopen/verification')
                if self.destination_check(self.destination)!=self.destination_identity:
                    raise StopRun('BLOCKED','Destination parent changed')
                plan=plan_open_save(self.snapshot,**self._context(),grid=self.grid,
                    previous_snapshot_id=self.before_commit,name_box_index=name_box_index,
                    selection_check=self._confirm_selection,
                    approved=True,overwrite_disposable=True,text=self.input_text,kind=self.input_kind,
                    approved_text=self.input_text,approved_kind=self.input_kind,formula_region=self.formula_region,
                    run_id=self.run_id,destination=self.destination,save_approved=True,toolbar_region=self.toolbar_region,point=point)
                _save(self.directory/'save-open-attempt.json',json.dumps(plan).encode())
                self.record(dict(event='save_open_intent',plan=plan,used=self.used))
                self._panel_baseline=self._call('list_windows',{'pid':self.pid,'include_accessory_windows':True})
                baseline=panel_inventory(self._panel_baseline,pid=self.pid,document_window=self.window)
                if (baseline[self.window].get('title')!=self.case.title
                        or baseline[self.window]['bounds']!=self.snapshot['window_bounds']):
                    raise ValueError('document changed before save click')
                if any(wid!=self.window and row.get('title')=='Save' for wid,row in baseline.items()):
                    raise ValueError('save panel already open')
                _save(self.directory/'save-window-baseline.json',json.dumps(self._panel_baseline).encode())
                # Discovery must not let a formerly fresh click age beyond its bound.
                _state(self.snapshot,**{k:v for k,v in self._context().items() if k!='cell'})
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
