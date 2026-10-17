"""Opt-in single input attempt on the original Calc ledger; no model endpoint."""
import json

from calc_input import plan_cell_input, plan_formula_focus, validate_cell_payload, inspect_committed_cell
from calc_edit import inspect_edit
from calc_targeting import confirm_selected_cell
from calc_selection import CalcSelectionTask, _save
from driver_smoke import StopRun


def verify_window_activation(value, pid, window_id):
    """A native request receipt is not a verified exact-window activation."""
    if not isinstance(value,dict):
        raise ValueError('exact activation response required')
    effect=value.get('exact_window_effect')
    observed=value.get('observed')
    if (value.get('status')!='activated'
            or value.get('code')!='bring_to_front_exact_window_verified'
            or value.get('activated') is not True or value.get('process_activated') is not True
            or type(value.get('pid')) is not int or value['pid']!=pid
            or type(value.get('window_id')) is not int or value['window_id']!=window_id
            or not isinstance(effect,dict) or not isinstance(observed,dict)
            or any(effect.get(k) is not True for k in (
                'verified','focused','front_in_process_on_display','target_visible_ordinary'))
            or any(type(observed.get(k)) is not int or observed[k]!=expected for k,expected in (
                ('frontmost_pid',pid),('focused_window_id',window_id),
                ('process_front_window_on_display',window_id)))
            or observed.get('front_process_matches_target') is False):
        raise ValueError('exact window activation unverified')
    return dict(pid=pid,window_id=window_id,status='WINDOW_ACTIVATION_OBSERVED',
                inputEffectVerified=False,businessStatus='UNVERIFIED')


class CalcInputTask(CalcSelectionTask):
    RAW_TOOLS = CalcSelectionTask.RAW_TOOLS | {'type_text'}
    SIDE_EFFECT_TOOLS = CalcSelectionTask.SIDE_EFFECT_TOOLS | {'type_text'}

    def __init__(self, *args, input_approved=False, overwrite_disposable=False,
                 approved_text=None, approved_kind=None, commit_approved=False,
                 formula_region=None, activation_approved=False, **kwargs):
        if type(activation_approved) is not bool:
            raise ValueError('explicit activation approval required')
        self.activation_approved=activation_approved
        if activation_approved:
            self.RAW_TOOLS=self.RAW_TOOLS|{'bring_to_front'}
            self.SIDE_EFFECT_TOOLS=self.SIDE_EFFECT_TOOLS|{'bring_to_front'}
        self.formula_region=None if formula_region is None else tuple(formula_region)
        if self.formula_region is not None:
            from calc_targeting import _number
            r=self.formula_region
            if len(r)!=4 or not all(_number(v) for v in r) or not 0<=r[0]<r[2] or not 0<=r[1]<r[3]:
                raise ValueError('valid trusted formula editor region required')
        if type(commit_approved) is not bool:
            raise ValueError('explicit boolean commit approval required')
        self.commit_approved=commit_approved
        if input_approved is not True or overwrite_disposable is not True:
            raise ValueError('explicit disposable input approval required')
        validate_cell_payload(approved_text, approved_kind)
        self.input_text, self.input_kind = approved_text, approved_kind
        super().__init__(*args, **kwargs)
        try:
            binding=dict(cell=self.cell,approvedText=approved_text,approvedKind=approved_kind,
                         inputApproved=True,overwriteDisposable=True)
            if commit_approved:binding['commitApproved']=True
            if activation_approved:binding['activationApproved']=True
            if self.formula_region is not None:binding['formulaRegion']=list(self.formula_region)
            path=self.directory/'input-binding.json'
            if path.exists() or path.is_symlink():
                if path.is_symlink() or json.loads(path.read_bytes())!=binding:
                    raise ValueError('original input binding changed')
            else:
                _save(path,json.dumps(binding,ensure_ascii=False).encode())
            self.record(dict(event='input_scope',binding=binding,singleAttempt=True,
                             commitPermitted=False,savePermitted=False))
        except Exception:
            self.close()
            raise

    def validate_raw(self, tool, args):
        if tool=='bring_to_front' and (not self.activation_approved or args!={
                'pid':self.pid,'window_id':self.window,'session':self.run_id}):
            raise StopRun('BLOCKED','Only original exact-window activation allowed')
        return super().validate_raw(tool,args)

    def activate_window_once(self, *, snapshot_id, name_box_index, resolve_name_box):
        """Explicit foreground change, never an automatic click fallback."""
        with self.lock:
            try:
                if (not self.activation_approved or self.phase!='CONFIRMED'
                        or self.stopped.is_set() or self.uncertain or self.lock_fd is None
                        or not self.snapshot or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Approved fresh selection required for activation')
                self.environment();self.lease.check();self.identity(self.pid)
                if self.used>22:
                    raise StopRun('BLOCKED','Reserve activation, focus, input and commit observations')
                confirm_selected_cell(self.snapshot,**self._context(),
                    previous_snapshot_id=self.before_click,name_box_index=name_box_index)
                intent=dict(snapshot_id=snapshot_id,pid=self.pid,window_id=self.window,
                            used=self.used,persistentForeground=True)
                _save(self.directory/'window-activation-attempt.json',json.dumps(intent).encode())
                self.record(dict(event='window_activation_intent',plan=intent))
                self.phase='WINDOW_ACTIVATION_ATTEMPTED';self.snapshot=None
                value=self._call('bring_to_front',dict(pid=self.pid,window_id=self.window,session=self.run_id))
                try:
                    proof=verify_window_activation(value,self.pid,self.window)
                except Exception:
                    self.uncertain=True
                    self.record(dict(event='window_activation_unverified',used=self.used))
                    raise
                result=self.observe()
                confirm_selected_cell(self.snapshot,**self._context(),
                    previous_snapshot_id=snapshot_id,name_box_index=resolve_name_box())
                self.record(dict(event='window_activation_observed',proof=proof,used=self.used))
                self.phase='CONFIRMED'
                return dict(result,**proof,inputPermitted=False,commitPermitted=False)
            except Exception:
                self.stop()
                raise

    def focus_input_once(self, *, snapshot_id, name_box_index, point, controls_region, editor_regions, resolve_name_box):
        """Trusted adapter regions; one screenshot click and independent edit check."""
        with self.lock:
            try:
                if (self.phase!='CONFIRMED' or self.stopped.is_set() or self.uncertain
                        or self.lock_fd is None or not self.snapshot
                        or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Confirmed fresh selection required before focus')
                self.environment();self.lease.check();self.identity(self.pid)
                if self.used>24:
                    raise StopRun('BLOCKED','Reserve focus, input and commit observations')
                plan=plan_formula_focus(self.snapshot,point=point,**self._context(),grid=self.grid,
                    previous_snapshot_id=self.before_click,name_box_index=name_box_index,
                    approved=True,overwrite_disposable=True,text=self.input_text,kind=self.input_kind,
                    approved_text=self.input_text,approved_kind=self.input_kind,formula_region=self.formula_region)
                _save(self.directory/'input-focus-attempt.json',json.dumps(plan,ensure_ascii=False).encode())
                self.record(dict(event='input_focus_intent',plan=plan,used=self.used))
                self.phase='INPUT_FOCUS_ATTEMPTED';self.snapshot=None
                self._call('click',dict(pid=self.pid,window_id=self.window,session=self.run_id,
                    **plan['target'],delivery_mode='foreground'))
                result=self.observe()
                context=self._context()
                confirm_selected_cell(self.snapshot,**context,
                    previous_snapshot_id=snapshot_id,name_box_index=resolve_name_box())
                context.pop('cell')
                evidence=inspect_edit(self.snapshot,**context,approved=True,
                    expected_text=plan['previousText'],controls_region=controls_region,editor_regions=editor_regions)
                self.record(dict(event='input_focus_observed',evidence=evidence,used=self.used))
                self.confirmed_focus=json.loads(json.dumps(dict(snapshot_id=self.snapshot['snapshot_id'],
                    expected_text=plan['previousText'],controls_region=controls_region,editor_regions=editor_regions)))
                self.phase='INPUT_FOCUS_OBSERVED'
                return dict(result,status='INPUT_FOCUS_OBSERVED',inputEffectVerified=False,
                    inputPermitted=False,commitPermitted=False,businessStatus='UNVERIFIED')
            except Exception:
                self.stop()
                raise

    def input_once(self, *, snapshot_id, name_box_index, text, kind):
        """name_box_index is selected by trusted adapter, never by the model."""
        with self.lock:
            try:
                if (self.phase not in ('CONFIRMED','INPUT_FOCUS_OBSERVED') or self.stopped.is_set() or self.uncertain
                        or self.lock_fd is None or not self.snapshot
                        or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Confirmed fresh selection required before input')
                self.lease.check()
                if self.used>28:
                    raise StopRun('BLOCKED','Reserve input and independent post-input observation')
                plan=plan_cell_input(self.snapshot,**self._context(),grid=self.grid,
                    previous_snapshot_id=self.before_click,name_box_index=name_box_index,
                    approved=True,overwrite_disposable=True,text=text,kind=kind,
                    approved_text=self.input_text,approved_kind=self.input_kind,
                    formula_region=self.formula_region,
                    focused_edit=self.confirmed_focus if self.phase=='INPUT_FOCUS_OBSERVED' else None)
                # Exclusive intent survives even an exception before raw dispatch.
                _save(self.directory/'input-attempt.json',json.dumps(plan,ensure_ascii=False).encode())
                self.phase='INPUT_ATTEMPTED'
                before=self.snapshot['snapshot_id']
                self.before_input=before
                self.snapshot=None
                self.record(dict(event='input_intent',plan=plan,used=self.used))
                self._call('type_text',dict(pid=self.pid,window_id=self.window,session=self.run_id,
                    **plan['target'],text=plan['text'],delivery_mode='foreground'))
                result=self.observe()
                if result['state']['snapshot_id']==before:
                    raise ValueError('post-input observation must be new')
                self.phase='AWAITING_INPUT_CONFIRMATION'
                return dict(result,status='INPUT_ATTEMPT_OBSERVED',inputEffectVerified=False,
                            inputPermitted=False,commitPermitted=False,businessStatus='UNVERIFIED')
            except Exception:
                self.stop()
                raise

    def confirm_input(self, *, snapshot_id, name_box_index, controls_region, editor_regions):
        """Trusted adapter supplies verification regions; no GUI action or commit."""
        with self.lock:
            try:
                if (self.phase!='AWAITING_INPUT_CONFIRMATION' or self.stopped.is_set()
                        or self.uncertain or self.lock_fd is None or not self.snapshot
                        or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Fresh post-input evidence required')
                self.environment();self.lease.check();self.identity(self.pid)
                context=self._context()
                confirm_selected_cell(self.snapshot,**context,
                    previous_snapshot_id=self.before_input,name_box_index=name_box_index)
                context.pop('cell')
                evidence=inspect_edit(self.snapshot,**context,approved=True,
                    expected_text=self.input_text,controls_region=controls_region,
                    editor_regions=editor_regions)
                result=dict(status='INPUT_OBSERVED',snapshot_id=snapshot_id,cell=self.cell,
                    text=self.input_text,kind=self.input_kind,editorEvidence=evidence,
                    inputEffectVerified=True,storageTypeVerified=False,commitPermitted=False,
                    inputPermitted=False,businessStatus='UNVERIFIED')
                self.record(dict(event='input_observed',result=result,used=self.used))
                self.confirmed_input=json.loads(json.dumps(dict(snapshot_id=snapshot_id,
                    name_box_index=name_box_index,controls_region=controls_region,
                    editor_regions=editor_regions)))
                self.phase='INPUT_OBSERVED'
                return result
            except Exception:
                self.stop()
                raise

    def commit_once(self, *, snapshot_id):
        """Single Accept on revalidated input evidence; no keyboard/save fallback."""
        with self.lock:
            try:
                if (not self.commit_approved or self.phase!='INPUT_OBSERVED'
                        or self.stopped.is_set() or self.uncertain or self.lock_fd is None
                        or not self.snapshot or snapshot_id!=self.snapshot['snapshot_id']
                        or snapshot_id!=self.confirmed_input['snapshot_id']):
                    raise StopRun('BLOCKED','Approved current input confirmation required')
                self.environment();self.lease.check();self.identity(self.pid)
                if self.used>28:
                    raise StopRun('BLOCKED','Reserve commit and post-commit observation')
                context=self._context()
                confirm_selected_cell(self.snapshot,**context,
                    previous_snapshot_id=self.before_input,
                    name_box_index=self.confirmed_input['name_box_index'])
                context.pop('cell')
                evidence=inspect_edit(self.snapshot,**context,approved=True,
                    expected_text=self.input_text,
                    controls_region=self.confirmed_input['controls_region'],
                    editor_regions=self.confirmed_input['editor_regions'])
                _save(self.directory/'commit-attempt.json',json.dumps(evidence).encode())
                self.record(dict(event='commit_intent',evidence=evidence,used=self.used))
                self.before_commit=snapshot_id
                self.phase='COMMIT_ATTEMPTED';self.snapshot=None
                self._call('click',dict(pid=self.pid,window_id=self.window,session=self.run_id,
                    element_token=evidence['accept']['element_token']))
                result=self.observe()
                if result['state']['snapshot_id']==snapshot_id:
                    raise ValueError('new post-commit observation required')
                self.phase='AWAITING_COMMIT_CONFIRMATION'
                return dict(result,status='COMMIT_ATTEMPT_OBSERVED',commitEffectVerified=False,
                    storageTypeVerified=False,inputPermitted=False,commitPermitted=False,
                    businessStatus='UNVERIFIED')
            except Exception:
                self.stop()
                raise

    def confirm_commit(self, *, snapshot_id, name_box_index):
        """Trusted post-commit verification; no action, save, or retry authority."""
        with self.lock:
            try:
                if (self.phase!='AWAITING_COMMIT_CONFIRMATION' or self.stopped.is_set()
                        or self.uncertain or self.lock_fd is None or not self.snapshot
                        or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Fresh original post-commit observation required')
                self.environment();self.lease.check();self.identity(self.pid)
                result=inspect_committed_cell(self.snapshot,**self._context(),grid=self.grid,
                    previous_snapshot_id=self.before_commit,name_box_index=name_box_index,
                    approved=True,overwrite_disposable=True,text=self.input_text,kind=self.input_kind,
                    approved_text=self.input_text,approved_kind=self.input_kind,formula_region=self.formula_region)
                self.record(dict(event='cell_commit_observed',result=result,used=self.used))
                self.phase='COMMIT_CONFIRMED'
                return result
            except Exception:
                self.stop()
                raise
