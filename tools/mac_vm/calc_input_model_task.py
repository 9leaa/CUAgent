"""Explicit input protocol adapter; not registered by the selection HTTP server."""
import json

from calc_input_task import CalcInputTask
from calc_model_task import CalcModelTask
from calc_selection import _save
from calc_targeting import _number, inspect_selected_cell, confirm_selected_cell


class CalcInputModelTask(CalcModelTask, CalcInputTask):
    protocol = 'calc-input-v1'
    stop_after_selection = False

    def __init__(self, *args, controls_region, editor_regions, **kwargs):
        # Trusted launcher supplies these, not a model tool invocation.
        regions=json.loads(json.dumps(dict(controls_region=controls_region,
            editor_regions=editor_regions),allow_nan=False))
        if not isinstance(editor_regions,(list,tuple)) or len(editor_regions)!=2:
            raise ValueError('two trusted editor regions required')
        for region in [controls_region,*editor_regions]:
            if (not isinstance(region,(list,tuple)) or len(region)!=4
                    or not all(_number(v) for v in region)
                    or not 0<=region[0]<region[2] or not 0<=region[1]<region[3]):
                raise ValueError('valid trusted region required')
        a,b=editor_regions
        if not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]):
            raise ValueError('independent editor regions required')
        self.input_regions=regions
        if kwargs.get('formula_region') is not None and list(kwargs['formula_region'])!=regions['editor_regions'][1]:
            raise ValueError('formula target must match trusted verification region')
        super().__init__(*args, **kwargs)
        try:
            path=self.directory/'input-verifier-binding.json'
            if path.exists() or path.is_symlink():
                if path.is_symlink() or json.loads(path.read_bytes())!=regions:
                    raise ValueError('input verifier binding changed')
            else:_save(path,json.dumps(regions).encode())
        except Exception:
            self.close()
            raise

    def activate_window(self, args):
        with self.lock:
            try:
                if not isinstance(args,dict) or set(args)!={'snapshot_id'}:
                    raise ValueError('only current activation snapshot allowed')
                result=self.activate_window_once(snapshot_id=args['snapshot_id'],
                    name_box_index=self._name_box(),resolve_name_box=self._name_box)
                confirmation=dict(status='WINDOW_ACTIVATION_OBSERVED',cell=self.cell,
                    snapshot_id=result['state']['snapshot_id'],inputEffectVerified=False,
                    inputPermitted=False,commitPermitted=False)
                return self.envelope(dict(result,confirmation=confirmation))
            except Exception:
                self.stop()
                raise

    def focus_input(self, args):
        with self.lock:
            try:
                if not isinstance(args,dict) or set(args)!={'snapshot_id','x','y'}:
                    raise ValueError('only current snapshot and focus point allowed')
                result=self.focus_input_once(snapshot_id=args['snapshot_id'],point=args,
                    name_box_index=self._name_box(),resolve_name_box=self._name_box,**self.input_regions)
                confirmation=dict(status='INPUT_FOCUS_OBSERVED',cell=self.cell,
                    snapshot_id=result['state']['snapshot_id'],inputEffectVerified=False,
                    inputPermitted=False,commitPermitted=False)
                return self.envelope(dict(result,confirmation=confirmation))
            except Exception:
                self.stop()
                raise

    def input_cell(self, args):
        with self.lock:
            try:
                if not isinstance(args,dict) or set(args)!={'snapshot_id','text','kind'}:
                    raise ValueError('only bound snapshot and approved payload allowed')
                result=self.input_once(**args,name_box_index=self._name_box())
                confirmation=self.confirm_input(snapshot_id=result['state']['snapshot_id'],
                    name_box_index=self._name_box(),**self.input_regions)
                return self.envelope(dict(result,status=confirmation['status'],confirmation=confirmation))
            except Exception:
                self.stop()
                raise

    def select_cell(self, args):
        with self.lock:
            if (self.phase!='NEW' or self.stopped.is_set() or self.uncertain or self.lock_fd is None):
                raise ValueError('selection stopped or unavailable')
            self.lease.check()
            if (isinstance(args,dict) and set(args)=={'snapshot_id'} and self.snapshot
                    and args['snapshot_id']==self.snapshot['snapshot_id']):
                # Approved pending edit recovery precedes the no-click shortcut.
                # Selection alone is not evidence that the cell is out of edit mode.
                if self._pending_approved_edit() is not None:
                    return super().select_cell(args)
                try:
                    inspect_selected_cell(self.snapshot,**self._context(),name_box_index=self._name_box())
                except ValueError:
                    return super().select_cell(args)
                try:
                    before=self.snapshot['snapshot_id']
                    self.record(dict(event='current_selection_check',snapshot_id=before,used=self.used))
                    result=self.observe()
                    confirmation=self._confirm_selection(self.snapshot,**self._context(),
                        previous_snapshot_id=before,name_box_index=self._name_box())
                    self.record(dict(event='selection_confirmed',route='already-selected',result=confirmation,used=self.used))
                    self.before_click=before  # Prior observation, no click on this route.
                    self.phase='CONFIRMED'
                    return self.envelope(dict(result,status=confirmation['status'],
                        selectionRoute='already-selected',confirmation=confirmation))
                except Exception:
                    self.stop()
                    raise
            return super().select_cell(args)

    def commit_cell(self, args):
        with self.lock:
            try:
                if not isinstance(args,dict) or set(args)!={'snapshot_id'}:
                    raise ValueError('only current confirmed snapshot allowed')
                result=self.commit_once(**args)
                self.stop()
                return self.envelope(result)
            except Exception:
                self.stop()
                raise
