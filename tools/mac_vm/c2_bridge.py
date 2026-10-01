"""C2 ownership/recovery extension; explicit separate control capability.

Developer recovery observations use the same budget and Driver policy. An
unresolved effect remains blocked; observation alone is not reconciliation.
"""
import json
import re
import threading
import time
import uuid
import os
import subprocess
from dataclasses import replace
from contextlib import contextmanager
from types import SimpleNamespace, MappingProxyType
from c1_bridge import C1Task, StopRun
from c0_bridge import Task
from c0_cases import UI_CASES

POLICY='c2-ownership-v1'
SESSION=re.compile(r'session-[A-Za-z0-9_-]{1,90}')

class C2ControlMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if not hasattr(self,'spec'):
            self.spec=SimpleNamespace(applications=(SimpleNamespace(title=self.case.title,bundle=self.case.bundle,executable=self.case.executable),))
            self.active=self.spec.applications[0];self.known_pids={};self.bound=set()
        self.recovery_thread=None
        self.recovery_epoch=None
        self.recovery_tools=frozenset(('list_windows','get_window_state'))
        self.recovery_kind='observation'
        self.model_context=threading.local()
        rows=[json.loads(line) for line in self.ledger.read_text().splitlines()]
        initial=[r for r in rows if r['event']=='c2_control_init']
        if len(initial)>1 or (initial and (initial[0].get('policy')!=POLICY or initial[0].get('case_id')!=self.case_id)):
            self.stopped.set();raise StopRun('BLOCKED','C2 policy identity differs')
        if not initial and self.used:
            self.stopped.set();raise StopRun('BLOCKED','Existing non-C2 run cannot become C2')
        if any(r['event']=='c2_reopen_identity_mismatch' for r in rows):
            self.stopped.set();raise StopRun('BLOCKED','Prior reopen changed process identity; independent repair required')
        self.epoch=0
        self.owner='model'
        self.session_owner=None
        for row in rows:
            if row['event']=='c2_control':
                if (type(row.get('epoch')) is not int or row.get('epoch')!=self.epoch+1 or row.get('owner') not in ('paused','human','model')
                    or row.get('policy')!=POLICY):
                    self.stopped.set();raise StopRun('BLOCKED','C2 ownership ledger invalid')
                self.epoch=row['epoch'];self.owner=row['owner'];self.session_owner=row.get('session_owner')
        if not initial:self.record({'event':'c2_control_init','policy':POLICY,'case_id':self.case_id})
        dispatches={r['call_id']:r for r in rows if r['event']=='dispatch'}
        terminals={r['call_id'] for r in rows if r['event'] in ('result','error','UNKNOWN') and r.get('call_id')}
        self.unresolved={r['call_id'] for r in rows if r['event']=='UNKNOWN'} | (set(dispatches)-terminals)
        self.uncertain=bool(self.unresolved)
        reconciled={r['call_id'] for r in rows if r['event']=='c2_reconciled_call'}
        if not reconciled<=self.unresolved:
            self.stopped.set();raise StopRun('BLOCKED','Reconciliation references no uncertain call')
        self.unresolved-=reconciled
        self.uncertain=bool(self.unresolved)
        self.pending_intent=None
        fault=os.environ.get('CUAGENT_C2_FAULT','none')
        if fault not in ('none','submit_response_timeout','process_exit_after_observe','window_close_after_observe','manual_document_edit','permission_revoke_after_observe'):raise StopRun('BLOCKED','Unreviewed fault injection')
        if fault=='manual_document_edit' and self.case_id!='document':raise StopRun('BLOCKED','Document fault needs the real reviewed document backend')
        if fault=='window_close_after_observe' and self.case_id!='input_correction':
            raise StopRun('BLOCKED','Window fault only for the reviewed keep-alive fixture')
        if fault=='permission_revoke_after_observe' and self.case_id!='input_correction':
            raise StopRun('BLOCKED','Permission fault only for the reviewed correction task')
        self.fault=fault
        self.fault_injected=any(r['event']=='c2_fault_injected' for r in rows)
        self.window_fault_armed=any(r['event']=='c2_window_fault_armed' for r in rows)
        self.document_fault_armed=any(r['event']=='c2_document_fault_armed' for r in rows)
        self.permission_fault_armed=any(r['event']=='c2_permission_fault_armed' for r in rows)
        closed=[r for r in rows if r['event']=='c2_window_closed']
        self.closed_window=closed[-1]['window_id'] if closed else None
        actual_transport=self.transport
        def guarded_transport(tool,payload):
            value=actual_transport(tool,payload)
            if (self.fault=='submit_response_timeout' and not self.fault_injected and tool=='click'
                and self.pending_intent and self.pending_intent['label']=='Submit'):
                self.fault_injected=True
                self.record({'event':'c2_fault_injected','fault':self.fault,'layer':'after_actual_driver_response',
                             'intent':self.pending_intent})
                raise TimeoutError('Controlled lost Submit response; inspect real effect before recovery')
            return value
        self.transport=guarded_transport
        # Restore identity/transfer context, never the usable snapshot.
        targets=[r for r in rows if r['event'] in ('target_bound','target_selected')]
        for row in targets:
            application=next((a for a in self.spec.applications if a.title==row.get('target')),None)
            if application is None or type(row.get('pid')) is not int or type(row.get('window_id')) is not int:
                self.stopped.set();raise StopRun('BLOCKED','Restored C2 target invalid')
            self.known_pids[application.bundle]=row['pid']
        if targets:
            last=targets[-1];self.active=next(a for a in self.spec.applications if a.title==last['target'])
            self.case=replace(self.case,bundle=self.active.bundle,title=self.active.title,executable=self.active.executable,
                app_name='Calculator' if self.active.bundle=='com.apple.calculator' else 'CUAgentFixtures')
            self.pid,self.window=last['pid'],last['window_id'];self.launch_args=self.launch_for(self.active)
        sources=[r for r in rows if r['event']=='calculator_transfer_source']
        if sources:self.transfer_value=sources[-1]['value']
        self.failure_injected=any(r['event']=='controlled_stale_refusal' for r in rows)
        self.snapshot=None
        if self.fault=='window_close_after_observe':
            self.launch_args={**self.launch_args,'additional_arguments':self.launch_args['additional_arguments']+['--keep-alive-after-close']}
        if initial:
            self.stopped.set()
            self.transition('paused','process_restart')

    def transition(self,owner,reason,session=None):
        # All callers hold admission lock. Persist before changing control state.
        self.record({'event':'c2_control','policy':POLICY,'epoch':self.epoch+1,
            'owner':owner,'reason':reason,'session_owner':session,'inflight':sorted(self.inflight)})
        self.epoch+=1;self.owner=owner;self.session_owner=session

    def launch_for(self,application):
        inherited=getattr(super(),'launch_for',None)
        if inherited:return inherited(application)
        return {'bundle_id':application.bundle,'creates_new_application_instance':True,
                'additional_arguments':['--task',self.case.mode,'--output',str(self.directory)]}

    def observe(self):
        result=super().observe()
        self.known_pids[self.active.bundle]=self.pid
        binding=(self.active.title,self.pid,self.window)
        if binding not in self.bound:
            self.bound.add(binding)
            self.record({'event':'target_bound','target':self.active.title,'pid':self.pid,'window_id':self.window})
        return result

    def record(self,row):
        if row.get('event')=='dispatch' and row.get('tool')=='click' and getattr(self,'pending_intent',None):
            row={**row,'intent':dict(self.pending_intent)}
        super().record(row)
        if (row.get('event')=='target_bound' and getattr(self,'fault',None)=='permission_revoke_after_observe'
            and not self.permission_fault_armed):
            self.permission_fault_armed=True
            self.record({'event':'c2_permission_fault_armed','pid':self.pid,'window_id':self.window,'used':self.used,
                         'permission_changed':False,'requires_real_guest_permission_change':True})
            self.stop()
            raise StopRun('BLOCKED','Paused for real developer-side guest permission revocation')
        if (row.get('event')=='completed_input' and getattr(self,'fault',None)=='manual_document_edit'
            and not self.document_fault_armed):
            self.document_fault_armed=True
            self.record({'event':'c2_document_fault_armed','pid':self.pid,'window_id':self.window,'used':self.used})
            self.stop()
            raise StopRun('BLOCKED','Document input complete; paused for reviewed GUI edit')
        if (row.get('event')=='target_bound' and getattr(self,'fault',None)=='window_close_after_observe'
            and not self.window_fault_armed):
            self.window_fault_armed=True
            self.record({'event':'c2_window_fault_armed','pid':self.pid,'window_id':self.window,'used':self.used})
            self.stop()
            raise StopRun('BLOCKED','Reviewed window-close fault paused after first observation')
        if (row.get('event')=='target_bound' and getattr(self,'fault',None)=='process_exit_after_observe'
            and not self.fault_injected):
            # A real executor exit, after the real read-only observation and
            # target identity are durable. No GUI input is replayed on restart.
            self.fault_injected=True
            self.record({'event':'c2_fault_injected','fault':self.fault,
                         'layer':'after_fresh_target_binding','exit_code':85,
                         'pid':self.pid,'window_id':self.window,'used':self.used})
            os._exit(85)
        if row.get('event')=='UNKNOWN' and row.get('tool') in ('click','type_text','set_value','scroll','press_key','launch_app','reopen_task_application') and hasattr(self,'epoch'):
            self.unresolved.add(row['call_id'])
            self.uncertain=True
            self.stop()

    def click(self,args):
        button=self.ui_element(args,('AXButton',))
        self.pending_intent={'label':button['label'],'snapshot_id':self.snapshot['snapshot_id'],
            'pid':self.pid,'window_id':self.window}
        try:return super().click(args)
        finally:self.pending_intent=None

    def reconcile_submit(self):
        # Independent developer control; no caller-provided outcome or proof.
        with self.lock, self.dispatch_lock:
            if (self.owner!='paused' or not self.stopped.is_set() or self.inflight or not self.uncertain
                or not self.snapshot or time.monotonic()-self.observed_at>30):
                raise StopRun('UNVERIFIED','Need paused task with fresh recovery evidence')
            rows=[json.loads(line) for line in self.ledger.read_text().splitlines()]
            dispatches={r['call_id']:r for r in rows if r['event']=='dispatch'}
            unknown={r['call_id'] for r in rows if r['event']=='UNKNOWN'}
            terminal={r['call_id'] for r in rows if r['event'] in ('result','error','UNKNOWN') and r.get('call_id')}
            unknown |= set(dispatches)-terminal
            unknown -= {r['call_id'] for r in rows if r['event']=='c2_reconciled_call'}
            if len(unknown)!=1:raise StopRun('UNVERIFIED','Need one attributable unresolved Submit')
            call_id=next(iter(unknown));call=dispatches[call_id];intent=call.get('intent',{})
            if (call['tool']!='click' or intent.get('label')!='Submit'
                or intent.get('pid')!=self.pid or intent.get('window_id')!=self.window
                or intent.get('snapshot_id')==self.snapshot['snapshot_id']
                or self.case_id not in ('input_correction','window_change','cross_app')
                or self.observed_value()!=self.case.expected):
                raise StopRun('UNVERIFIED','Unknown action not matched by fresh actual Submit effect')
            actions=[r['label'] for r in rows if r['event']=='completed_action']+['Submit']
            if not self.verify_ui_trajectory(rows,actions):
                raise StopRun('UNVERIFIED','Submission file/effects/full trajectory do not prove the original action')
            self.record({'event':'c2_reconciled_call','call_id':call_id,'verdict':'applied',
                'snapshot_id':self.snapshot['snapshot_id'],'pid':self.pid,'window_id':self.window,
                'proof':'fresh real status, fixed submission file, effects and complete preceding trajectory'})
            self.record({'event':'completed_action','label':'Submit','snapshot_id':intent['snapshot_id'],
                'effect_snapshot_id':self.snapshot['snapshot_id'],'effect_proven':True,'reconciled_call_id':call_id})
            self.unresolved=set();self.uncertain=False
            return {'reconciled':call_id,'verdict':'applied','no_replay':True,'used':self.used}

    def verify(self):
        self.observe()
        rows=[json.loads(line) for line in self.ledger.read_text().splitlines()]
        actions=[r['label'] for r in rows if r['event']=='completed_action']
        display=self.observed_value()
        path=self.task_file('result.txt')
        result=path.read_text().strip()
        readback=any(r['event']=='result' and r.get('tool')=='read_result' and r.get('value')==self.case.expected+'\n' for r in rows)
        dispatches={r['call_id'] for r in rows if r['event']=='dispatch'}
        completed={r['call_id'] for r in rows if r['event']=='result' and r.get('call_id')}
        receipts={r['call_id'] for r in rows if r['event']=='c2_reconciled_call'}
        unknown={r['call_id'] for r in rows if r['event']=='UNKNOWN'}
        passed=(self.verify_ui_trajectory(rows,actions) and display==result==self.case.expected and readback
            and not self.uncertain and not self.stopped.is_set() and self.owner=='model'
            and completed|receipts==dispatches and unknown<=receipts)
        report={'status':'SUCCEEDED' if passed else 'UNVERIFIED','actions':actions,'fresh_display':display,
            'file_readback':result,'expected':self.case.expected,'raw_calls':self.used,'case_id':self.case_id,
            'reconciled_calls':sorted(receipts),'policy':POLICY,'control_epoch':self.epoch}
        with self.task_file('verification.json').open('x') as stream:json.dump(report,stream,indent=2)
        return report

    def control_status(self):
        with self.dispatch_lock:
            return {'owner':self.owner,'epoch':self.epoch,'used':self.used,'stopped':self.stopped.is_set(),
                    'inflight':sorted(self.inflight),'uncertain':self.uncertain}

    def stop(self):
        with self.dispatch_lock:
            result=super().stop()
            self.snapshot=None
            self.transition('paused','stop',self.session_owner)
            return {**result,'epoch':self.epoch,'inflight':sorted(self.inflight)}

    def claim_human(self):
        with self.dispatch_lock:
            if not self.stopped.is_set() or self.owner!='paused' or self.inflight or self.uncertain:
                raise StopRun('BLOCKED','Stop and account for in-flight/UNKNOWN before human control')
            self.snapshot=None
            self.transition('human','takeover')
            return {'owner':self.owner,'epoch':self.epoch,'used':self.used}

    def _admit(self,tool):
        recovery=self.recovery_thread==threading.get_ident()
        if recovery:
            if (not self.stopped.is_set() or self.owner not in ('paused','human') or self.inflight
                or self.recovery_epoch!=self.epoch
                or tool not in self.recovery_tools or self.used>=30):
                raise StopRun('BLOCKED','Recovery permits only budgeted observations')
            call_id=str(uuid.uuid4())
            self.record({'event':'dispatch','tool':tool,'used':self.used+1,'call_id':call_id,
                         'control_epoch':self.epoch,'recovery_observation':self.recovery_kind=='observation',
                         'developer_control':self.recovery_kind!='observation'})
            self.used+=1;self.inflight.add(call_id)
            return call_id
        if self.owner!='model' or getattr(self.model_context,'epoch',self.epoch)!=self.epoch:
            raise StopRun('BLOCKED','C2 desktop is not model-owned by this request')
        return super()._admit(tool)

    @contextmanager
    def model_request(self,session_id,epoch):
        current=self.authorize_session(session_id,epoch)
        self.model_context.epoch=current
        try:yield
        finally:del self.model_context.epoch

    def recovery_observe(self):
        # Not a model endpoint. No launch/replay is allowed during recovery.
        with self.lock:
            with self.dispatch_lock:
                if not self.stopped.is_set() or self.owner not in ('paused','human') or self.inflight or self.pid is None:
                    raise StopRun('BLOCKED','Need paused bound task without in-flight calls')
                self.recovery_thread=threading.get_ident()
                self.recovery_epoch=self.epoch
                self.recovery_tools=frozenset(('list_windows','get_window_state'))
                self.recovery_kind='observation'
                self.snapshot=None;self.window=None
            try:
                result=super().observe()
                self.record({'event':'c2_recovery_observed','epoch':self.epoch,'snapshot_id':self.snapshot['snapshot_id'],
                             'pid':self.pid,'window_id':self.window,'used':self.used})
                return result
            finally:
                self.recovery_thread=None
                self.recovery_epoch=None

    @contextmanager
    def _developer_control_calls(self,tools,required_fault):
        # A private, narrow developer capability, never a model endpoint.
        with self.lock:
            with self.dispatch_lock:
                if (self.fault!=required_fault or self.owner!='human'
                    or not self.stopped.is_set() or self.inflight or self.uncertain):
                    raise StopRun('BLOCKED','Need reconciled human ownership for reviewed window fault')
                self.recovery_thread=threading.get_ident();self.recovery_epoch=self.epoch
                self.recovery_tools=frozenset(tools);self.recovery_kind='window_fault'
            try:yield
            finally:
                self.recovery_thread=None;self.recovery_epoch=None
                self.recovery_tools=frozenset(('list_windows','get_window_state'));self.recovery_kind='observation'

    def close_current_window(self):
        with self._developer_control_calls(('click','list_windows'),'window_close_after_observe'):
            state=self.snapshot
            if self.fault_injected or not state or time.monotonic()-self.observed_at>30:
                raise StopRun('BLOCKED','Need a fresh original window; fault is single-use')
            self.identity(self.pid)
            bounds=state.get('window_bounds',{})
            roots={e['element_index'] for e in state.get('elements',[]) if e.get('role')=='AXWindow' and e.get('label')==self.case.title}
            candidates=[]
            for element in state.get('elements',[]):
                frame=element.get('frame',{})
                if (element.get('role')=='AXButton' and not element.get('label')
                    and element.get('parent_index') in roots and element.get('enabled') is True
                    and 'AXPress' in element.get('actions',[]) and all(k in frame for k in ('x','y','w','h'))
                    and all(k in bounds for k in ('x','y')) and 0<frame['w']<=22 and 0<frame['h']<=22
                    and 0<=frame['x']-bounds['x']<=28 and 0<=frame['y']-bounds['y']<=28):candidates.append(element)
            if len(candidates)!=1 or not state.get('screenshot_frame_valid'):
                raise StopRun('UNVERIFIED','Need one actual fresh title-bar close button')
            button=candidates[0];old_window=self.window
            self.record({'event':'c2_window_close_attempt','snapshot_id':state['snapshot_id'],'pid':self.pid,'window_id':old_window,
                         'element_index':button['element_index'],'element_token':button['element_token']})
            self.snapshot=None
            self.raw('click',{'pid':self.pid,'window_id':old_window,'session':self.run_id,
                            'element_index':button['element_index'],'element_token':button['element_token']})
            windows=self.raw('list_windows',{'pid':self.pid}).get('windows',[])
            if any(w.get('window_id')==old_window and w.get('pid')==self.pid and w.get('is_on_screen') for w in windows):
                raise StopRun('UNVERIFIED','Original window still visible')
            self.closed_window=old_window;self.fault_injected=True
            self.record({'event':'c2_window_closed','pid':self.pid,'window_id':old_window,'used':self.used})
            self.record({'event':'c2_fault_injected','fault':self.fault,'layer':'actual_driver_close_and_fresh_inventory',
                         'pid':self.pid,'window_id':old_window,'used':self.used})
            return {'closed_window':old_window,'pid':self.pid,'used':self.used}

    def reopen_window(self):
        with self._developer_control_calls(('list_windows','reopen_task_application'),'window_close_after_observe'):
            if self.closed_window is None:raise StopRun('BLOCKED','No independently closed reviewed window')
            self.identity(self.pid)
            windows=self.raw('list_windows',{'pid':self.pid}).get('windows',[])
            if any(w.get('pid')==self.pid and w.get('is_on_screen') and w.get('title')==self.case.title for w in windows):
                raise StopRun('BLOCKED','Reviewed task window already visible; do not recreate')
            call=self.admit('reopen_task_application')
            try:
                subprocess.run(['/usr/bin/open','-a','/Users/mvpagent/Applications/CUAgentFixtures.app'],
                               check=True,timeout=10,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.record({'event':'result','tool':'reopen_task_application','call_id':call,
                             'value':{'activation_requested':True,'pid':self.pid,'not_window_proof':True}})
            except Exception as error:
                self.record({'event':'UNKNOWN','tool':'reopen_task_application','call_id':call,'error':type(error).__name__})
                raise
            finally:self.inflight.discard(call)
            try:self.identity(self.pid)
            except Exception:
                self.uncertain=True
                self.record({'event':'c2_reopen_identity_mismatch','original_pid':self.pid})
                raise
            self.window=None;self.snapshot=None
            self.record({'event':'c2_window_reopen_requested','pid':self.pid,'old_window_id':self.closed_window,'used':self.used})
            return {'requires_recovery_observation':True,'pid':self.pid,'used':self.used}

    def resume(self,session_id,epoch):
        with self.dispatch_lock:
            if (self.owner!='human' or not self.stopped.is_set() or self.inflight or self.uncertain
                or type(epoch) is not int or epoch!=self.epoch or not isinstance(session_id,str) or not SESSION.fullmatch(session_id)
                or self.used>=29
                or (self.closed_window is not None and self.window==self.closed_window)
                or not self.snapshot or time.monotonic()-self.observed_at>30):
                raise StopRun('BLOCKED','Need current ownership, fresh recovery observation, remaining budget and reconciled effects')
            self.identity(self.pid)
            if self.inflight or epoch!=self.epoch:raise StopRun('BLOCKED','Ownership changed during resume validation')
            self.transition('model','explicit_resume',session_id)
            self.snapshot=None
            self.stopped.clear()
            return {'owner':'model','epoch':self.epoch,'used':self.used,'requires_new_observation':True}

    def authorize_session(self,session_id,epoch):
        with self.dispatch_lock:
            if self.owner!='model' or self.stopped.is_set() or type(epoch) is not int or epoch!=self.epoch:
                raise StopRun('BLOCKED','Session control epoch is stale or paused')
            if self.session_owner is None:
                if not isinstance(session_id,str) or not SESSION.fullmatch(session_id):
                    raise StopRun('BLOCKED','Valid official session required')
                self.transition('model','initial_session',session_id)
            elif self.session_owner!=session_id:raise StopRun('BLOCKED','Another session owns this task')
            return self.epoch

class C2Task(C2ControlMixin,C1Task):
    """Original six C1 task backends with the C2 ownership layer."""


DOCUMENT_INTERFERENCE='C2 developer edit: drifted harbor-000.'


class C2DocumentTask(C2ControlMixin,Task):
    """The real C0 NSTextView/save-sheet backend, not a C1 field substitute."""
    RAW_TOOLS=Task.RAW_TOOLS|frozenset(('set_value',))
    SIDE_EFFECT_TOOLS=Task.SIDE_EFFECT_TOOLS|frozenset(('set_value',))
    def __init__(self,*args,case_id='document',**kwargs):
        if case_id!='document':raise StopRun('BLOCKED','Only reviewed real document task')
        super().__init__(*args,case_id=case_id,registry=MappingProxyType({'document':UI_CASES['document']}),**kwargs)

    def body_value(self):
        if not self.snapshot or time.monotonic()-self.observed_at>30:raise StopRun('UNVERIFIED','Need fresh actual document observation')
        bodies=[e for e in self.snapshot.get('elements',[]) if e.get('role')=='AXTextArea' and e.get('label')=='Document Body' and self.in_window(e,self.snapshot)]
        if len(bodies)!=1:raise StopRun('UNVERIFIED','Need unique reviewed document body')
        return bodies[0].get('value','')

    def raw(self,tool,args):
        if tool=='set_value' and args!=getattr(self,'replacement_payload',None):
            raise StopRun('BLOCKED','Only internally grounded fixed document replacement')
        return super().raw(tool,args)

    def replace_body(self,text):
        if text not in (self.case.expected,DOCUMENT_INTERFERENCE):raise StopRun('BLOCKED','Unreviewed document replacement')
        state=self.snapshot
        if not state or time.monotonic()-self.observed_at>30:raise StopRun('BLOCKED','Fresh body observation required')
        bodies=[e for e in state.get('elements',[]) if e.get('role')=='AXTextArea' and e.get('label')=='Document Body' and self.in_window(e,state)]
        if len(bodies)!=1:raise StopRun('BLOCKED','Unique actual body required')
        body=bodies[0]
        self.replacement_payload={'pid':self.pid,'window_id':self.window,'session':self.run_id,
                                  'element_index':body['element_index'],'element_token':body['element_token'],'value':text}
        self.snapshot=None
        try:return self.raw('set_value',self.replacement_payload)
        finally:self.replacement_payload=None

    def type_text(self,args):
        if set(args)!={'snapshot_id','element_index','element_token','text'}:raise StopRun('BLOCKED','Unexpected document input fields')
        body=self.ui_element(args,('AXTextArea',))
        if body.get('label')!='Document Body' or args['text']!=self.case.expected:raise StopRun('BLOCKED','Unreviewed document field/input')
        if not body.get('value'):return super().type_text(args)
        result=self.replace_body(args['text'])
        self.record({'event':'completed_input','label':'Document Body','text':args['text']})
        return result

    def edit_document(self):
        with self._developer_control_calls(('set_value',),'manual_document_edit'):
            if self.fault_injected or self.body_value()!=self.case.expected:
                raise StopRun('BLOCKED','Need first actual intended document content; edit is single-use')
            state=self.snapshot
            body=next(e for e in state['elements'] if e.get('role')=='AXTextArea' and e.get('label')=='Document Body' and self.in_window(e,state))
            self.record({'event':'c2_document_edit_attempt','snapshot_id':state['snapshot_id'],'pid':self.pid,'window_id':self.window,
                         'before':self.body_value(),'text':DOCUMENT_INTERFERENCE,'element_token':body['element_token']})
            self.replace_body(DOCUMENT_INTERFERENCE)
            self.fault_injected=True
            self.record({'event':'c2_document_edited','pid':self.pid,'window_id':self.window,'text':DOCUMENT_INTERFERENCE,'used':self.used,
                         'requires_fresh_effect_observation':True})
            self.record({'event':'c2_fault_injected','fault':self.fault,'layer':'actual_driver_document_body_replacement','used':self.used})
            return {'requires_recovery_observation':True,'used':self.used}

    def resume(self,session_id,epoch):
        if self.fault=='manual_document_edit' and (not self.fault_injected or self.body_value()!=DOCUMENT_INTERFERENCE):
            raise StopRun('UNVERIFIED','Need actual changed GUI body before ownership return')
        return super().resume(session_id,epoch)

    def verify_ui_trajectory(self,rows,actions):
        if self.fault!='manual_document_edit':return super().verify_ui_trajectory(rows,actions)
        inputs=[(i,r) for i,r in enumerate(rows) if r['event']=='completed_input']
        edits=[(i,r) for i,r in enumerate(rows) if r['event']=='c2_document_edited']
        attempts=[(i,r) for i,r in enumerate(rows) if r['event']=='c2_document_edit_attempt']
        resumes=[i for i,r in enumerate(rows) if r['event']=='c2_control' and r.get('reason')=='explicit_resume']
        if (actions!=['Save Document','Save'] or len(inputs)!=2 or len(edits)!=1 or len(attempts)!=1 or len(resumes)!=1
            or [(r.get('label'),r.get('text')) for _,r in inputs]!=list(self.case.fields)*2
            or not inputs[0][0]<attempts[0][0]<edits[0][0]<resumes[0]<inputs[1][0]):return False
        expected=self.case.expected;attempt=attempts[0][1]
        states=[(i,r['value']) for i,r in enumerate(rows) if r['event']=='result' and r.get('tool')=='get_window_state']
        def body(state):
            bodies=[e.get('value','') for e in state.get('elements',[]) if e.get('role')=='AXTextArea' and e.get('label')=='Document Body']
            return bodies[0] if len(bodies)==1 else None
        bound=lambda state:state.get('pid')==attempt['pid'] and state.get('window_id')==attempt['window_id'] and state.get('screenshot_frame_valid')
        original=any(inputs[0][0]<i<attempts[0][0] and s.get('snapshot_id')==attempt['snapshot_id'] and bound(s) and body(s)==expected for i,s in states)
        changed=any(edits[0][0]<i<resumes[0] and bound(s) and body(s)==DOCUMENT_INTERFERENCE for i,s in states)
        model_changed=any(resumes[0]<i<inputs[1][0] and bound(s) and body(s)==DOCUMENT_INTERFERENCE for i,s in states)
        save_index=next((i for i,r in enumerate(rows) if r['event']=='completed_action' and r.get('label')=='Save Document'),-1)
        corrected=any(inputs[1][0]<i<save_index and bound(s) and body(s)==expected for i,s in states)
        data=json.loads(self.task_file('document-save.json').read_text())
        return (original and changed and model_changed and corrected
                and data=={'saved':True,'filename':'task-note.txt','text':expected}
                and self.task_file('task-note.txt').read_text()==expected)


def task_for_case(directory,*,case_id,**kwargs):
    return (C2DocumentTask if case_id=='document' else C2Task)(directory,case_id=case_id,**kwargs)


if __name__=='__main__':
    from c0_bridge import main
    from c1_bridge import REGISTRY
    main(task_class=task_for_case,registry=MappingProxyType({**REGISTRY,'document':UI_CASES['document']}),stage='C2')
