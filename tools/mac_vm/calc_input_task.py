"""Opt-in single input attempt on the original Calc ledger; no model endpoint."""
import json

from calc_input import plan_cell_input, validate_cell_payload
from calc_selection import CalcSelectionTask, _save
from driver_smoke import StopRun


class CalcInputTask(CalcSelectionTask):
    RAW_TOOLS = CalcSelectionTask.RAW_TOOLS | {'type_text'}
    SIDE_EFFECT_TOOLS = CalcSelectionTask.SIDE_EFFECT_TOOLS | {'type_text'}

    def __init__(self, *args, input_approved=False, overwrite_disposable=False,
                 approved_text=None, approved_kind=None, **kwargs):
        if input_approved is not True or overwrite_disposable is not True:
            raise ValueError('explicit disposable input approval required')
        validate_cell_payload(approved_text, approved_kind)
        self.input_text, self.input_kind = approved_text, approved_kind
        super().__init__(*args, **kwargs)
        try:
            binding=dict(cell=self.cell,approvedText=approved_text,approvedKind=approved_kind,
                         inputApproved=True,overwriteDisposable=True)
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

    def input_once(self, *, snapshot_id, name_box_index, text, kind):
        """name_box_index is selected by trusted adapter, never by the model."""
        with self.lock:
            try:
                if (self.phase!='CONFIRMED' or self.stopped.is_set() or self.uncertain
                        or self.lock_fd is None or not self.snapshot
                        or snapshot_id!=self.snapshot['snapshot_id']):
                    raise StopRun('BLOCKED','Confirmed fresh selection required before input')
                self.lease.check()
                if self.used>28:
                    raise StopRun('BLOCKED','Reserve input and independent post-input observation')
                plan=plan_cell_input(self.snapshot,**self._context(),grid=self.grid,
                    previous_snapshot_id=self.before_click,name_box_index=name_box_index,
                    approved=True,overwrite_disposable=True,text=text,kind=kind,
                    approved_text=self.input_text,approved_kind=self.input_kind)
                # Exclusive intent survives even an exception before raw dispatch.
                _save(self.directory/'input-attempt.json',json.dumps(plan,ensure_ascii=False).encode())
                self.phase='INPUT_ATTEMPTED'
                before=self.snapshot['snapshot_id']
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
