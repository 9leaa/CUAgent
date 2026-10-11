"""DSH-facing selection adapter; no model-controlled verification target."""
import json
import re

from c0_bridge import Task
from calc_selection import CalcSelectionTask, _save
from calc_targeting import _number, _in_window, _elements
from calc_edit import plan_edit_cancel

PROTOCOL = 'calc-selection-v1'


class CalcModelTask(CalcSelectionTask):
    def __init__(self, *args, session_id, name_box_grid, edit_cancel=None, **kwargs):
        if not isinstance(session_id,str) or not re.fullmatch(r'session-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',session_id):
            raise ValueError('trusted official session required')
        if (not isinstance(name_box_grid,(tuple,list)) or len(name_box_grid)!=4
                or not all(_number(v) for v in name_box_grid)
                or not 0<=name_box_grid[0]<name_box_grid[2] or not 0<=name_box_grid[1]<name_box_grid[3]):
            raise ValueError('trusted name box region required')
        if edit_cancel is not None:
            if (not isinstance(edit_cancel,dict) or set(edit_cancel)!={'approved','expected_text','controls_region','editor_regions'}
                    or edit_cancel['approved'] is not True or not isinstance(edit_cancel['expected_text'],str)
                    or not edit_cancel['expected_text'] or len(edit_cancel['expected_text'].encode())>256):
                raise ValueError('explicit disposable edit binding required')
            edit_cancel=json.loads(json.dumps(edit_cancel,allow_nan=False))
        self.edit_cancel=edit_cancel
        self._edit_cancel_attempted=False
        self.session_id,self.name_box_grid=session_id,tuple(name_box_grid)
        super().__init__(*args,**kwargs)
        try:
            path=self.directory/'model-binding.json'
            binding=dict(protocol=PROTOCOL,sessionId=session_id,nameBoxGrid=list(name_box_grid))
            if edit_cancel is not None:binding['editCancel']=edit_cancel
            if path.exists() or path.is_symlink():
                if path.is_symlink() or json.loads(path.read_bytes())!=binding:
                    raise ValueError('model binding changed')
            else: _save(path,json.dumps(binding).encode())
        except Exception:
            self.close()
            raise

    def envelope(self, result):
        return dict(result,protocol=PROTOCOL,runId=self.run_id,sessionId=self.session_id,
                    cell=self.cell,inputPermitted=False,businessStatus='UNVERIFIED',used=self.used)

    def observe(self):
        return self.envelope(super().observe())

    def _edit_plan(self):
        if self.edit_cancel is None:return None
        return plan_edit_cancel(self.snapshot,**{k:v for k,v in self._context().items() if k!='cell'},**self.edit_cancel)

    def _pending_approved_edit(self):
        try:return self._edit_plan()
        except ValueError:return None

    def _cancel_edit(self):
        if self.phase!='NEW' or self._edit_cancel_attempted or self.stopped.is_set() or self.uncertain:
            raise ValueError('edit cancellation already attempted or unavailable')
        plan=self._edit_plan()
        if plan is None:raise ValueError('edit cancellation not approved')
        self.lease.check()
        if self.used>28:raise ValueError('reserve cancellation and post-action observation')
        self._edit_cancel_attempted=True
        self.record(dict(event='edit_cancel_intent',plan=plan,used=self.used))
        previous=self.snapshot['snapshot_id'];self.snapshot=None
        try:
            self._call('click',dict(pid=self.pid,window_id=self.window,session=self.run_id,**plan['target']))
            result=self.observe()
            if result['state']['snapshot_id']==previous:raise ValueError('new cancellation observation required')
            if self._pending_approved_edit() is not None:raise ValueError('approved edit still active after cancellation')
            # A fresh screenshot is evidence for the next model decision, not a
            # claim that cancellation or the final selection succeeded.
            return self.envelope(dict(result,status='EDIT_CANCEL_ATTEMPT_OBSERVED'))
        except Exception:
            self.stop()
            raise

    def _name_box(self):
        state=self.snapshot
        left,top,right,bottom=self.name_box_grid
        if right>state['screenshot_width'] or bottom>state['screenshot_height']:
            raise ValueError('name box outside screenshot')
        indexed=_elements(state)
        if indexed is None: raise ValueError('malformed elements')
        scale=state['screenshot_scale'];bounds=state['window_bounds']
        matches=[]
        for element in indexed.values():
            if element.get('role')!='AXComboBox' or not _in_window(element,indexed,self.case.title): continue
            frame=element.get('frame',{})
            if not isinstance(frame,dict) or not all(_number(frame.get(k)) for k in ('x','y','w','h')): continue
            x=(frame['x']-bounds['x'])*scale;y=(frame['y']-bounds['y'])*scale
            w=frame['w']*scale;h=frame['h']*scale
            if w>0 and h>0 and left<=x and top<=y and x+w<=right and y+h<=bottom:
                matches.append(element['element_index'])
        if len(matches)!=1: raise ValueError('name box is missing or ambiguous')
        return matches[0]

    def select_cell(self,args):
        with self.lock:
            if self.phase!='NEW' or self.stopped.is_set() or self.uncertain or self.lock_fd is None:
                raise ValueError('selection stopped or unavailable')
            self.lease.check()
            if (not isinstance(args,dict) or set(args) not in ({'snapshot_id'},{'snapshot_id','x','y'},{'snapshot_id','cancel_edit'})
                    or not self.snapshot or args['snapshot_id']!=self.snapshot['snapshot_id']):
                raise ValueError('same-snapshot selection required')
            if 'cancel_edit' in args:
                if args['cancel_edit'] is not True:raise ValueError('explicit cancellation required')
                return self._cancel_edit()
            if self._pending_approved_edit() is not None:
                if self._edit_cancel_attempted:raise ValueError('edit remains active; no retry')
                return self.envelope(dict(status='NEEDS_EDIT_CANCEL',snapshot_id=self.snapshot['snapshot_id']))
            result=super().select(point=args if 'x' in args else None)
            if result['status']=='NEEDS_SCREENSHOT_POINT': return self.envelope(result)
            try:
                confirmation=super().confirm(name_box_index=self._name_box())
                self.stop()
                return self.envelope(dict(result,status=confirmation['status'],confirmation=confirmation))
            except Exception:
                self.stop()
                raise

    def charge_rejection(self,op,prior_used,reason):
        # Authenticated protocol refusals consume the same persistent budget,
        # but cannot grant a public raw tool or create another Driver action.
        with self.dispatch_lock:
            self.snapshot=None
            try:
                if self.used==prior_used and not self.stopped.is_set() and self.used<30:
                    self.environment();self.lease.check()
                    call_id=Task._admit(self,'rejected_calc_request')
                    try:
                        self.record(dict(event='result',tool='rejected_calc_request',call_id=call_id,
                                         value=dict(status='refused',reason=reason)))
                    finally: self.inflight.discard(call_id)
            finally: self.stop()
