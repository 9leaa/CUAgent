"""One reviewed Calculator or fixed UI task; only mvpagent in VirtualMac.

No shell/file/desktop passthrough endpoints. Raw evidence stays in the guest.
"""
import base64
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from driver_smoke import require_vm, calculator_identity, display_value, Calls, StopRun, BUNDLE
from c0_cases import CALCULATORS, UI_CASES, TASKS
from c0_identity import app_identity

ALLOWED = {'All Clear', 'Clear', *map(str, range(10)), 'Multiply', 'Equals'}

class Task:
    def __init__(self, directory, transport=Calls.cli, identity=None, *, approved=False, case_id='mul12_34', registry=TASKS):
        if not approved:
            raise StopRun('BLOCKED', 'Explicit fixed-task approval required')
        if case_id not in registry:
            raise StopRun('BLOCKED', 'Task is not in the reviewed fixed registry')
        self.case_id, self.case = case_id, registry[case_id]
        self.is_calculator = case_id in CALCULATORS
        self.allowed = frozenset(self.case.actions if self.is_calculator else self.case.buttons)
        self.launch_args = {'bundle_id':self.case.bundle}
        if not self.is_calculator:
            self.launch_args.update(creates_new_application_instance=True,
                                   additional_arguments=['--task', self.case.mode, '--output',str(directory)])
        if directory.is_symlink():
            raise StopRun('BLOCKED', 'Task directory must not be a symlink')
        self.directory = directory
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.transport = transport
        self.identity = identity or (lambda pid: app_identity(pid, self.case.executable))
        self.lock = threading.RLock()
        self.dispatch_lock = threading.RLock()
        self.audit_lock = threading.RLock()
        self.stopped = threading.Event()
        self.pid = self.window = None
        self.snapshot = None
        self.observed_at = 0
        self.run_id = directory.name
        self.ledger = directory / 'trace.jsonl'
        self.used = 0
        self.uncertain = False
        self.inflight = set()
        self.save_confirmation_pending = False
        self.pending_save_snapshot = None
        self.save_effect_recorded = False
        if self.ledger.is_symlink():
            raise StopRun('BLOCKED', 'Audit ledger must not be a symlink')
        if self.ledger.exists():
            rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
            if any(row.get('case_id', 'mul12_34') != case_id for row in rows if row['event']=='approval'):
                raise StopRun('BLOCKED', 'Cannot switch case inside an existing run')
            dispatches = [row for row in rows if row['event'] == 'dispatch']
            if any(row.get('run_id') != self.run_id for row in rows):
                raise StopRun('BLOCKED', 'Audit run identity mismatch')
            if [row.get('used') for row in dispatches] != list(range(1, len(dispatches)+1)):
                raise StopRun('BLOCKED', 'Audit budget sequence invalid')
            self.used = len(dispatches)
            # A restarted bridge cannot silently replay an unfinished task.
            if self.used or any(row['event']=='stop' for row in rows): self.stopped.set()
        self.record({'event':'approval', 'allowed_app': self.case.bundle, 'case_id': case_id,
                     'operations':['observe','reviewed task buttons','reviewed task field input' if not self.is_calculator else 'no text input','write/read result.txt'],
                     'authorization':'user requested the staged fixed Computer Use tasks in this conversation'})

    def record(self, row):
        try:
            with self.audit_lock:
                fd = os.open(self.ledger, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'a', encoding='utf8') as f:
                    f.write(json.dumps({'at':time.time(), 'run_id':self.run_id, **row})+'\n')
                    f.flush(); os.fsync(f.fileno())
        except Exception:
            self.stopped.set()
            raise

    def stop(self):
        # Linearizes with admission, never waits for a running transport.
        with self.dispatch_lock:
            self.stopped.set()
            self.record({'event':'stop', 'inflight':sorted(self.inflight)})
        return {'stopped':True}

    def admit(self, tool):
        with self.dispatch_lock:
            return self._admit(tool)

    def _admit(self, tool):
        if self.stopped.is_set(): raise StopRun('BLOCKED', 'Task stopped; new dispatch denied')
        if self.used >= 30: raise StopRun('BLOCKED', '30 raw-request budget exhausted')
        if self.uncertain and tool not in ('get_window_state', 'read_result') and not tool.startswith('rejected_'):
            raise StopRun('UNVERIFIED', 'Prior action UNKNOWN; only observation is allowed')
        call_id = str(uuid.uuid4())
        self.record({'event':'dispatch','tool':tool,'used':self.used+1,'call_id':call_id})
        self.used += 1
        self.inflight.add(call_id)
        return call_id

    def raw(self, tool, args):
        if tool not in ('launch_app', 'list_windows', 'get_window_state', 'click', 'type_text', 'scroll', 'press_key'):
            raise StopRun('BLOCKED', 'Raw tool not permitted')
        if tool=='press_key' and (self.case_id!='document' or not self.save_confirmation_pending
                or args!={'pid':self.pid,'window_id':self.window,'session':self.run_id,'key':'return','delivery_mode':'foreground'}):
            raise StopRun('BLOCKED','Only grounded Save confirmation key permitted')
        if (tool=='type_text' and self.is_calculator) or (tool=='scroll' and self.case_id!='scroll'):
            raise StopRun('BLOCKED','Tool not approved for this fixed task')
        if tool == 'launch_app' and args != self.launch_args:
            raise StopRun('BLOCKED', 'Application not permitted')
        if tool != 'launch_app' and (args.get('pid') != self.pid or self.pid is None):
            raise StopRun('BLOCKED', 'PID not permitted')
        if tool in ('get_window_state', 'click', 'type_text', 'scroll', 'press_key') and args.get('window_id') != self.window:
            raise StopRun('BLOCKED', 'Window not permitted')
        if self.pid: self.identity(self.pid)
        with self.dispatch_lock:
            call_id = self.admit(tool)
        # Calls admitted before stop are in-flight, not cancelled side effects.
        explicitly_refused=False
        try:
            value = self.transport(tool, args)
            if isinstance(value,dict) and (value.get('status')=='refused' or value.get('effect')=='refused'):
                explicitly_refused=True
                self.record({'event':'result','tool':tool,'value':value,'call_id':call_id})
                raise StopRun('BLOCKED','Driver explicitly refused the action; no completed effect')
            if (not isinstance(value, dict) or value.get('status') in ('error', 'failed') or 'error' in value
                or value.get('isError') is True or value.get('code') in ('delivery_failed','foreground_unavailable','background_unavailable','permission_denied')):
                raise StopRun('UNVERIFIED', 'Driver did not return a successful response')
            self.record({'event':'result','tool':tool,'value':value,'call_id':call_id})
            return value
        except Exception as exc:
            if tool in ('click','launch_app','type_text','scroll','press_key') and not explicitly_refused: self.uncertain = True
            self.record({'event':'UNKNOWN' if self.uncertain else 'error','tool':tool,'error':type(exc).__name__,'call_id':call_id})
            raise
        finally:
            with self.dispatch_lock:
                self.inflight.discard(call_id)

    def observe(self):
        self.snapshot = None
        if self.pid is None:
            launched = self.raw('launch_app', self.launch_args)
            if launched.get('bundle_id') != self.case.bundle or type(launched.get('pid')) is not int:
                raise StopRun('BLOCKED', 'Calculator launch identity mismatch')
            self.pid = launched['pid']
        if self.window is None:
            windows = self.raw('list_windows', {'pid':self.pid})
            candidates = [w for w in windows.get('windows',[]) if w.get('pid')==self.pid
                          and w.get('title')==self.case.title and w.get('app_name')==self.case.app_name
                          and w.get('is_on_screen')]
            if len(candidates)!=1: raise StopRun('UNVERIFIED','Need one Calculator window; observe again')
            self.window = candidates[0]['window_id']
        path=self.directory / ('state-%02d.png' % (self.used+1))
        if path.exists(): raise StopRun('BLOCKED','Evidence path already exists')
        state=self.raw('get_window_state',{'pid':self.pid,'window_id':self.window,
                      'session':self.run_id,'screenshot_out_file':str(path)})
        if (state.get('pid')!=self.pid or state.get('window_id')!=self.window
            or state.get('app_name')!=self.case.app_name or state.get('window_title')!=self.case.title
            or not state.get('snapshot_id') or state.get('degraded_reason')
            or not state.get('screenshot_frame_valid')):
            raise StopRun('UNVERIFIED','Fresh usable Calculator observation required')
        png=path.read_bytes()
        if not png.startswith(b'\x89PNG\r\n\x1a\n'): raise StopRun('UNVERIFIED','Invalid screenshot')
        (self.directory/('state-%02d.json'%self.used)).write_text(json.dumps(state))
        self.snapshot, self.observed_at=state,time.monotonic()
        if (self.case_id=='document' and self.pending_save_snapshot and not self.save_effect_recorded
            and 'Saved task-note.txt' in state.get('tree_markdown','') and self.task_file('task-note.txt').is_file()):
            self.record({'event':'completed_action','label':'Save','snapshot_id':self.pending_save_snapshot,
                         'effect_snapshot_id':state['snapshot_id'],'proof':'fresh Saved UI and actual task file'})
            self.save_effect_recorded=True
        return {'state':state,'png':base64.b64encode(png).decode(), 'used':self.used}

    def click(self, args):
        if set(args)!={'snapshot_id','element_index','element_token'}: raise StopRun('BLOCKED','Unexpected click fields')
        state=self.snapshot
        if not state or args['snapshot_id']!=state['snapshot_id'] or time.monotonic()-self.observed_at>30:
            raise StopRun('BLOCKED','Observation missing or stale; observe again')
        roots={e['element_index'] for e in state.get('elements',[]) if e.get('role')=='AXWindow'
               and e.get('label')==self.case.title}
        buttons=[e for e in state.get('elements',[]) if e.get('element_index')==args['element_index']
                 and e.get('element_token')==args['element_token'] and e.get('role')=='AXButton'
                 and (e.get('parent_index') in roots if self.is_calculator else self.in_window(e,state))
                 and e.get('label') in self.allowed
                 and e.get('enabled') is True and 'AXPress' in e.get('actions',[])]
        if len(buttons)!=1: raise StopRun('BLOCKED','Not an approved Calculator button')
        self.snapshot=None
        if self.case_id=='document' and buttons[0]['label']=='Save':
            result=self.click_save_panel(buttons[0],state)
        else:
            result = self.raw('click',{'pid':self.pid,'window_id':self.window,'session':self.run_id,
                                   'element_index':args['element_index'],'element_token':args['element_token']})
        if self.case_id=='document' and buttons[0]['label']=='Save':
            self.pending_save_snapshot=args['snapshot_id']
            self.record({'event':'attempted_action','label':'Save','snapshot_id':args['snapshot_id']})
        else:
            self.record({'event':'completed_action','label':buttons[0]['label'],'snapshot_id':args['snapshot_id']})
        return result

    def click_save_panel(self, button, root_state):
        # AppKit exposes the Save sheet under the document AX tree, but its
        # CGWindowID is different: AX input under the document ID is refused.
        # Ground the selected button in the fresh document image + AX frame
        # and bind its exact independently listed sheet before pixel delivery.
        windows=self.raw('list_windows',{'pid':self.pid})
        panels=[w for w in windows.get('windows',[]) if w.get('pid')==self.pid
                and w.get('app_name')==self.case.app_name and w.get('title')=='Save task document'
                and w.get('is_on_screen') is True]
        if len(panels)!=1:raise StopRun('UNVERIFIED','Need one owned Save panel')
        panel=panels[0];bounds=panel.get('bounds',{});frame=button.get('frame',{})
        if not root_state.get('screenshot_frame_valid') or not all(k in frame for k in ('x','y','w','h')):
            raise StopRun('UNVERIFIED','Save button frame not grounded in fresh root observation')
        x,y=frame['x']+frame['w']/2,frame['y']+frame['h']/2
        if (frame['w']<=0 or frame['h']<=0 or not all(k in bounds for k in ('x','y','width','height'))
            or not bounds['x']<=frame['x']<frame['x']+frame['w']<=bounds['x']+bounds['width']
            or not bounds['y']<=frame['y']<frame['y']+frame['h']<=bounds['y']+bounds['height']):
            raise StopRun('BLOCKED','Save button outside the independently owned panel')
        # Do not snapshot the unresolved sheet between the parent snapshot and
        # input: its composited capture is not a usable coordinate frame.
        root_bounds=root_state.get('window_bounds',{})
        root_scale=root_state.get('screenshot_scale')
        if (root_state.get('degraded_reason') or type(root_scale) not in (int,float) or root_scale<=0
            or not all(k in root_bounds for k in ('x','y','width','height'))
            or not root_bounds['x']<=frame['x']<frame['x']+frame['w']<=root_bounds['x']+root_bounds['width']
            or not root_bounds['y']<=frame['y']<frame['y']+frame['h']<=root_bounds['y']+root_bounds['height']):
            raise StopRun('UNVERIFIED','Save button outside fresh parent screenshot frame')
        self.record({'event':'save_panel_grounding','root_window':self.window,'root_snapshot':root_state['snapshot_id'],
                     'panel_window':panel['window_id'],'panel_bounds':bounds,'button_frame':frame,
                     'source':'fresh parent PNG and AX button; separately owned sheet inventory'})
        self.save_confirmation_pending=True
        root_window=self.window
        self.window=panel['window_id']
        try:
            return self.raw('press_key',{'pid':self.pid,'window_id':self.window,'session':self.run_id,
                            'key':'return','delivery_mode':'foreground'})
        finally:
            self.save_confirmation_pending=False
            self.window=root_window

    def in_window(self, element, state):
        by_index={e['element_index']:e for e in state.get('elements',[])}
        seen=set()
        while element and element.get('element_index') not in seen:
            seen.add(element.get('element_index'))
            if element.get('role')=='AXWindow': return element.get('label')==self.case.title
            element=by_index.get(element.get('parent_index'))
        return False

    def ui_element(self, args, roles):
        state=self.snapshot
        if (not state or args.get('snapshot_id')!=state['snapshot_id']
            or time.monotonic()-self.observed_at>30):
            raise StopRun('BLOCKED','Fresh observation required')
        matches=[e for e in state.get('elements',[]) if e.get('element_index')==args.get('element_index')
                 and e.get('element_token')==args.get('element_token') and e.get('role') in roles
                 and e.get('enabled',True) is True and self.in_window(e,state)]
        if len(matches)!=1: raise StopRun('BLOCKED','Element outside approved task window')
        return matches[0]

    def type_text(self, args):
        if self.is_calculator or set(args)!={'snapshot_id','element_index','element_token','text'}:
            raise StopRun('BLOCKED','Typing not approved for this task')
        element=self.ui_element(args,('AXTextField','AXTextArea'))
        if (element.get('label'),args['text']) not in self.case.fields:
            raise StopRun('BLOCKED','Unreviewed field or input')
        self.snapshot=None
        result=self.raw('type_text',{'pid':self.pid,'window_id':self.window,'session':self.run_id,
                                    'element_index':args['element_index'],'element_token':args['element_token'],
                                    'text':args['text']})
        self.record({'event':'completed_input','label':element.get('label'),'text':args['text']})
        return result

    def scroll(self, args):
        if self.case_id!='scroll' or set(args)!={'snapshot_id','x','y','direction','amount'}:
            raise StopRun('BLOCKED','Scroll not approved for this task')
        state=self.snapshot
        if not state or args['snapshot_id']!=state['snapshot_id'] or time.monotonic()-self.observed_at>30:
            raise StopRun('BLOCKED','Fresh screenshot required for pixel scrolling')
        scale=state.get('screenshot_scale')
        if (not state.get('screenshot_frame_valid') or not isinstance(scale,(int,float)) or scale<=0
            or state.get('window_bounds',{}).get('width')!=640 or state.get('window_bounds',{}).get('height')!=508):
            raise StopRun('UNVERIFIED','Fixed task scroll-region frame not proven')
        # Native fixture has a non-resizable viewport at x20..620/y53..443 points.
        # Keep a margin inside it, in the fresh screenshot's independently validated scale.
        if (type(args['x']) not in (int,float) or type(args['y']) not in (int,float)
            or not 25*scale<=args['x']<=610*scale or not 60*scale<=args['y']<=425*scale
            or args['direction'] not in ('up','down') or type(args['amount']) is not int or not 1<=args['amount']<=10):
            raise StopRun('BLOCKED','Unreviewed scroll target or range')
        self.snapshot=None
        result=self.raw('scroll',{'pid':self.pid,'window_id':self.window,'session':self.run_id,
                                 'x':args['x'],'y':args['y'],
                                 'direction':args['direction'],'amount':args['amount'],'by':'page'})
        self.record({'event':'completed_scroll','direction':args['direction'],'amount':args['amount']})
        return result

    def charge_rejection(self, op, prior_used, reason):
        # An authenticated reviewed tool failure before Driver dispatch still consumes budget.
        if self.used!=prior_used or self.stopped.is_set() or self.used>=30:return
        with self.dispatch_lock:
            call_id=self.admit('rejected_'+op)
            try:self.record({'event':'result','tool':'rejected_'+op,'call_id':call_id,'value':{'status':'refused','reason':reason}})
            finally:self.inflight.discard(call_id)

    def task_file(self, name):
        path=self.directory/name
        if path.is_symlink(): raise StopRun('BLOCKED','Task artifact symlink refused')
        return path

    def observed_value(self):
        if self.is_calculator: return display_value(self.snapshot)
        tree=self.snapshot.get('tree_markdown','').split('\n- ',1)[0]
        if self.case_id=='form':
            labels=re.findall(r'AXStaticText = "([^"\n]+)"',tree)
            matches=[text for text in labels if text.startswith('Submitted: ')]
            if len(matches)==1: return matches[0]
        elif self.case_id=='scroll':
            viewport=json.loads(self.task_file('viewport.json').read_text())
            if viewport.get('targetVisible') is True and 'TARGET visible' in tree and 'TARGET: '+viewport['target'] in tree:
                return viewport['target']
        elif self.case_id=='document' and 'Saved task-note.txt' in tree:
            return self.task_file('task-note.txt').read_text()
        raise StopRun('UNVERIFIED','No fresh independently grounded UI result')

    def write_result(self, args):
        if set(args)!={'snapshot_id','value'} or not self.snapshot or args['snapshot_id']!=self.snapshot['snapshot_id']:
            raise StopRun('BLOCKED','Write requires a fresh observed display')
        if time.monotonic()-self.observed_at>30: raise StopRun('BLOCKED','Result observation stale')
        value=self.observed_value()
        if args['value']!=value: raise StopRun('UNVERIFIED','Result does not match observed AX display')
        with self.dispatch_lock:
            call_id = self.admit('write_result')
            try:
                with (self.directory/'result.txt').open('x') as f: f.write(value+'\n')
                (self.directory/'final_state.json').write_text(json.dumps(self.snapshot))
                self.record({'event':'result','tool':'write_result','value':value,'call_id':call_id})
            except Exception:
                self.stopped.set()
                raise
            finally:
                self.inflight.discard(call_id)
        return {'created':'result.txt','value':value,'used':self.used}

    def read_result(self):
        with self.dispatch_lock:
            call_id = self.admit('read_result')
            try:
                path = self.directory/'result.txt'
                if path.is_symlink(): raise StopRun('BLOCKED', 'Result symlink denied')
                value=path.read_text()
                self.record({'event':'result','tool':'read_result','value':value,'call_id':call_id})
            except Exception as exc:
                self.record({'event':'error','tool':'read_result','error':type(exc).__name__,'call_id':call_id})
                raise
            finally:
                self.inflight.discard(call_id)
        return {'content':value,'used':self.used}

    def verify(self):
        # The independent expected value never enters a model-facing route.
        self.observe()
        rows=[json.loads(line) for line in self.ledger.read_text().splitlines()]
        actions=[row['label'] for row in rows if row['event']=='completed_action']
        expected=list(self.case.actions) if self.is_calculator else None
        display=self.observed_value()
        result_path = self.directory/'result.txt'
        if result_path.is_symlink(): raise StopRun('BLOCKED', 'Result symlink denied')
        result=result_path.read_text().strip()
        readback = any(row['event']=='result' and row.get('tool')=='read_result'
                       and row.get('value')==self.case.expected+'\n' for row in rows)
        completed = {row.get('call_id') for row in rows if row['event']=='result'}
        dispatched = {row.get('call_id') for row in rows if row['event']=='dispatch'}
        trajectory=actions==expected if self.is_calculator else self.verify_ui_trajectory(rows,actions)
        passed=(trajectory and display==self.case.expected and result==self.case.expected and readback
                and not self.uncertain and completed==dispatched and not self.stopped.is_set())
        report={'status':'SUCCEEDED' if passed else 'UNVERIFIED','actions':actions,
                'fresh_display':display,'file_readback':result,'expected':self.case.expected,'raw_calls':self.used,
                'case_id':self.case_id}
        (self.directory/'verification.json').write_text(json.dumps(report,indent=2))
        return report

    def verify_ui_trajectory(self, rows, actions):
        if self.case_id=='form':
            data=json.loads(self.task_file('submission.json').read_text())
            inputs=[(r.get('label'),r.get('text')) for r in rows if r['event']=='completed_input']
            return (actions==['Submit'] and sorted(inputs)==sorted(self.case.fields)
                    and data=={'code':'cedar-42','note':'local form test','submitted':True})
        if self.case_id=='scroll':
            data=json.loads(self.task_file('viewport.json').read_text())
            return (any(r['event']=='completed_scroll' for r in rows) and not actions
                    and data.get('targetVisible') is True and data.get('originY',0)>0
                    and data.get('target')==self.case.expected)
        if self.case_id=='document':
            inputs=[(r.get('label'),r.get('text')) for r in rows if r['event']=='completed_input']
            data=json.loads(self.task_file('document-save.json').read_text())
            return (actions==['Save Document','Save'] and inputs==list(self.case.fields)
                    and data=={'saved':True,'filename':'task-note.txt','text':self.case.expected}
                    and self.task_file('task-note.txt').read_text()==self.case.expected)
        return False

def main(task_class=Task, registry=TASKS, stage='C0'):
    require_vm()
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--approve-task', '--approve-calculator', dest='approved', action='store_true')
    parser.add_argument('--case', choices=tuple(registry), default='mul12_34' if stage=='C0' else None, required=stage!='C0')
    args=parser.parse_args()
    if not args.run.replace('_','').replace('-','').isalnum() or len(args.run)>80: raise ValueError('Invalid run id')
    root=Path.home()/'C0Evidence'
    if root.is_symlink(): raise ValueError('Evidence root symlink')
    root.mkdir(mode=0o700,exist_ok=True)
    owner=(root/'bridge.lock').open('a');fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
    task=task_class(root/args.run, approved=args.approved, case_id=args.case)
    token=secrets.token_urlsafe(32)
    verifier_token=secrets.token_urlsafe(32)
    (task.directory/'bridge-token').write_text(token);os.chmod(task.directory/'bridge-token',0o600)
    (task.directory/'verifier-token').write_text(verifier_token);os.chmod(task.directory/'verifier-token',0o600)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def reply(self,code,value):
            data=json.dumps(value).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            # Only a narrowly scoped authenticated client is admitted.
            self.reply(405,{'error':'POST only'})
        def do_POST(self):
            auth = self.headers.get('Authorization')
            if self.client_address[0]!='192.168.64.1' or auth not in ('Bearer '+token, 'Bearer '+verifier_token):
                return self.reply(403,{'error':'Forbidden'})
            prior_used=None;op=None
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<4096: raise ValueError('Invalid body length')
                body=json.loads(self.rfile.read(size));op=body.get('op');payload=body.get('args',{})
                if set(body)-{'op','args'}: raise ValueError('Unexpected envelope fields')
                if op=='verify' and auth!='Bearer '+verifier_token:
                    return self.reply(403, {'error':'Independent verifier authorization required'})
                if auth=='Bearer '+verifier_token and op not in ('verify','stop'):
                    return self.reply(403, {'error':'Verifier cannot act'})
                if op=='stop':
                    if payload!={}: raise ValueError('Unexpected stop fields')
                    return self.reply(200,task.stop())
                with task.lock:
                    prior_used=task.used
                    if op=='observe' and payload=={}: result=task.observe()
                    elif op=='click': result=task.click(payload)
                    elif op=='type_text': result=task.type_text(payload)
                    elif op=='scroll': result=task.scroll(payload)
                    elif op=='select_target' and hasattr(task,'select_target'): result=task.select_target(payload)
                    elif op=='write_result': result=task.write_result(payload)
                    elif op=='read_result' and payload=={}: result=task.read_result()
                    elif op=='verify' and payload=={}: result=task.verify()
                    else: raise ValueError('Operation not permitted')
                    self.reply(200,result)
            except Exception as exc:
                if prior_used is not None and op in ('observe','click','type_text','scroll','write_result','read_result','select_target'):
                    with task.lock:task.charge_rejection(op,prior_used,str(exc))
                task.record({'event':'denied','error':str(exc)})
                self.reply(409,{'error':str(exc),'used':task.used})
    # Fixed private VM interface; never wildcard or host-side desktop service.
    server=ThreadingHTTPServer(('192.168.64.3',args.port),Handler)
    server.timeout=1;deadline=time.monotonic()+3600
    print('C0_BRIDGE_READY',flush=True)
    try:
        while time.monotonic()<deadline: server.handle_request()
    finally:server.server_close();task.stopped.set()

if __name__=='__main__': main()
