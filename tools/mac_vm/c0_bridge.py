"""One authorized Calculator task; runs only as mvpagent in VirtualMac.

No shell/file/desktop passthrough endpoints. Raw evidence stays in the guest.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from driver_smoke import require_vm, calculator_identity, display_value, Calls, StopRun, BUNDLE

ALLOWED = {'All Clear', 'Clear', *map(str, range(10)), 'Multiply', 'Equals'}

class Task:
    def __init__(self, directory, transport=Calls.cli, identity=calculator_identity, *, approved=False):
        if not approved:
            raise StopRun('BLOCKED', 'Explicit Calculator task approval required')
        if directory.is_symlink():
            raise StopRun('BLOCKED', 'Task directory must not be a symlink')
        self.directory = directory
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.transport, self.identity = transport, identity
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
        if self.ledger.is_symlink():
            raise StopRun('BLOCKED', 'Audit ledger must not be a symlink')
        if self.ledger.exists():
            rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
            dispatches = [row for row in rows if row['event'] == 'dispatch']
            if any(row.get('run_id') != self.run_id for row in rows):
                raise StopRun('BLOCKED', 'Audit run identity mismatch')
            if [row.get('used') for row in dispatches] != list(range(1, len(dispatches)+1)):
                raise StopRun('BLOCKED', 'Audit budget sequence invalid')
            self.used = len(dispatches)
            # A restarted bridge cannot silently replay an unfinished task.
            if self.used or any(row['event']=='stop' for row in rows): self.stopped.set()
        self.record({'event':'approval', 'allowed_app': BUNDLE,
                     'operations':['observe', 'click permitted Calculator button', 'write/read result.txt'],
                     'authorization':'user requested C0-01 Calculator task in this conversation'})

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
        if self.uncertain and tool not in ('get_window_state', 'read_result'):
            raise StopRun('UNVERIFIED', 'Prior action UNKNOWN; only observation is allowed')
        call_id = str(uuid.uuid4())
        self.record({'event':'dispatch','tool':tool,'used':self.used+1,'call_id':call_id})
        self.used += 1
        self.inflight.add(call_id)
        return call_id

    def raw(self, tool, args):
        if tool not in ('launch_app', 'list_windows', 'get_window_state', 'click'):
            raise StopRun('BLOCKED', 'Raw tool not permitted')
        if tool == 'launch_app' and args != {'bundle_id': BUNDLE}:
            raise StopRun('BLOCKED', 'Application not permitted')
        if tool != 'launch_app' and (args.get('pid') != self.pid or self.pid is None):
            raise StopRun('BLOCKED', 'PID not permitted')
        if tool in ('get_window_state', 'click') and args.get('window_id') != self.window:
            raise StopRun('BLOCKED', 'Window not permitted')
        if self.pid: self.identity(self.pid)
        with self.dispatch_lock:
            call_id = self.admit(tool)
        # Calls admitted before stop are in-flight, not cancelled side effects.
        try:
            value = self.transport(tool, args)
            if not isinstance(value, dict) or value.get('status') in ('refused', 'error', 'failed') or 'error' in value:
                raise StopRun('UNVERIFIED', 'Driver did not return a successful response')
            self.record({'event':'result','tool':tool,'value':value,'call_id':call_id})
            return value
        except Exception as exc:
            if tool in ('click','launch_app'): self.uncertain = True
            self.record({'event':'UNKNOWN' if self.uncertain else 'error','tool':tool,'error':type(exc).__name__,'call_id':call_id})
            raise
        finally:
            with self.dispatch_lock:
                self.inflight.discard(call_id)

    def observe(self):
        self.snapshot = None
        if self.pid is None:
            launched = self.raw('launch_app', {'bundle_id':BUNDLE})
            if launched.get('bundle_id') != BUNDLE or type(launched.get('pid')) is not int:
                raise StopRun('BLOCKED', 'Calculator launch identity mismatch')
            self.pid = launched['pid']
        if self.window is None:
            windows = self.raw('list_windows', {'pid':self.pid})
            candidates = [w for w in windows.get('windows',[]) if w.get('pid')==self.pid
                          and w.get('title')=='Calculator' and w.get('app_name')=='Calculator'
                          and w.get('is_on_screen')]
            if len(candidates)!=1: raise StopRun('UNVERIFIED','Need one Calculator window; observe again')
            self.window = candidates[0]['window_id']
        path=self.directory / ('state-%02d.png' % (self.used+1))
        if path.exists(): raise StopRun('BLOCKED','Evidence path already exists')
        state=self.raw('get_window_state',{'pid':self.pid,'window_id':self.window,
                      'session':self.run_id,'screenshot_out_file':str(path)})
        if (state.get('pid')!=self.pid or state.get('window_id')!=self.window
            or state.get('app_name')!='Calculator' or state.get('window_title')!='Calculator'
            or not state.get('snapshot_id') or state.get('degraded_reason')
            or not state.get('screenshot_frame_valid')):
            raise StopRun('UNVERIFIED','Fresh usable Calculator observation required')
        png=path.read_bytes()
        if not png.startswith(b'\x89PNG\r\n\x1a\n'): raise StopRun('UNVERIFIED','Invalid screenshot')
        (self.directory/('state-%02d.json'%self.used)).write_text(json.dumps(state))
        self.snapshot, self.observed_at=state,time.monotonic()
        return {'state':state,'png':base64.b64encode(png).decode(), 'used':self.used}

    def click(self, args):
        if set(args)!={'snapshot_id','element_index','element_token'}: raise StopRun('BLOCKED','Unexpected click fields')
        state=self.snapshot
        if not state or args['snapshot_id']!=state['snapshot_id'] or time.monotonic()-self.observed_at>30:
            raise StopRun('BLOCKED','Observation missing or stale; observe again')
        roots={e['element_index'] for e in state.get('elements',[]) if e.get('role')=='AXWindow'
               and e.get('label')=='Calculator'}
        buttons=[e for e in state.get('elements',[]) if e.get('element_index')==args['element_index']
                 and e.get('element_token')==args['element_token'] and e.get('role')=='AXButton'
                 and e.get('parent_index') in roots and e.get('label') in ALLOWED
                 and e.get('enabled') is True and 'AXPress' in e.get('actions',[])]
        if len(buttons)!=1: raise StopRun('BLOCKED','Not an approved Calculator button')
        self.snapshot=None
        result = self.raw('click',{'pid':self.pid,'window_id':self.window,'session':self.run_id,
                               'element_index':args['element_index'],'element_token':args['element_token']})
        self.record({'event':'completed_action','label':buttons[0]['label'],'snapshot_id':args['snapshot_id']})
        return result

    def write_result(self, args):
        if set(args)!={'snapshot_id','value'} or not self.snapshot or args['snapshot_id']!=self.snapshot['snapshot_id']:
            raise StopRun('BLOCKED','Write requires a fresh observed display')
        if time.monotonic()-self.observed_at>30: raise StopRun('BLOCKED','Result observation stale')
        value=display_value(self.snapshot)
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
        expected=['All Clear','1','2','Multiply','3','4','Equals']
        display=display_value(self.snapshot)
        result_path = self.directory/'result.txt'
        if result_path.is_symlink(): raise StopRun('BLOCKED', 'Result symlink denied')
        result=result_path.read_text().strip()
        readback = any(row['event']=='result' and row.get('tool')=='read_result'
                       and row.get('value')=='408\n' for row in rows)
        completed = {row.get('call_id') for row in rows if row['event']=='result'}
        dispatched = {row.get('call_id') for row in rows if row['event']=='dispatch'}
        passed=(actions==expected and display=='408' and result=='408' and readback
                and not self.uncertain and completed==dispatched and not self.stopped.is_set())
        report={'status':'SUCCEEDED' if passed else 'UNVERIFIED','actions':actions,
                'fresh_display':display,'file_readback':result,'expected':'408','raw_calls':self.used}
        (self.directory/'verification.json').write_text(json.dumps(report,indent=2))
        return report

def main():
    require_vm()
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--approve-calculator', action='store_true')
    args=parser.parse_args()
    if not args.run.replace('_','').replace('-','').isalnum() or len(args.run)>80: raise ValueError('Invalid run id')
    root=Path.home()/'C0Evidence'
    if root.is_symlink(): raise ValueError('Evidence root symlink')
    root.mkdir(mode=0o700,exist_ok=True)
    owner=(root/'bridge.lock').open('a');fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
    task=Task(root/args.run, approved=args.approve_calculator)
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
                    if op=='observe' and payload=={}: result=task.observe()
                    elif op=='click': result=task.click(payload)
                    elif op=='write_result': result=task.write_result(payload)
                    elif op=='read_result' and payload=={}: result=task.read_result()
                    elif op=='verify' and payload=={}: result=task.verify()
                    else: raise ValueError('Operation not permitted')
                    self.reply(200,result)
            except Exception as exc:
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
