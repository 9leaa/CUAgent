"""Bounded VM HTTP launcher for the official DSH Calc tools; never grants a lease."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import threading
import time

from calc_model_task import CalcModelTask, PROTOCOL
from calc_input_model_task import CalcInputModelTask
from calc_save_model_task import CalcSaveModelTask
from calc_save import workbook_destination
from calc_input import validate_cell_payload
from calc_targeting import _number
from calc_selection import SHARED_LOCK, _save
from desktop_control import LeaseController
from desktop_lease import LeaseGate
from desktop_tools_http import tools_server
from desktop_control_http import control_server
from calc_runtime import CalcGuestRuntime
from real_app_bridge import require_unlocked
from driver_smoke import diagnostic_cli_binding

UUID = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'

def edit_binding(args):
    if not getattr(args,'approve_cancel_edit',False):return {}
    return dict(edit_cancel=dict(approved=True,expected_text=args.pending_edit_text,
        controls_region=args.edit_controls_region,editor_regions=[args.edit_body_region,args.edit_formula_region]))


def input_binding(args):
    fields=[getattr(args,key,None) for key in ('input_text','input_kind','input_controls_region',
                                              'input_body_region','input_formula_region')]
    approved=getattr(args,'approve_input',False)
    overwrite=getattr(args,'overwrite_disposable',False)
    commit=getattr(args,'approve_commit',False)
    activation=getattr(args,'approve_window_activation',False)
    if type(activation) is not bool:raise ValueError('explicit activation boolean required')
    target=getattr(args,'input_target','cell')
    if target not in ('cell','formula'):raise ValueError('reviewed input target mode required')
    if not approved and not overwrite and not commit and not activation and target=='cell' and all(v is None for v in fields):return None
    if not approved or not overwrite or any(v is None for v in fields):
        raise ValueError('explicit input approval, disposable overwrite, payload and regions required')
    text,kind,controls,body,formula=fields
    validate_cell_payload(text,kind)
    for region in (controls,body,formula):
        if (len(region)!=4 or not all(_number(v) for v in region)
                or not 0<=region[0]<region[2] or not 0<=region[1]<region[3]):
            raise ValueError('valid input verification regions required')
    if not (body[2]<=formula[0] or formula[2]<=body[0] or body[3]<=formula[1] or formula[3]<=body[1]):
        raise ValueError('independent input editor regions required')
    result=dict(input_approved=True,overwrite_disposable=True,approved_text=text,approved_kind=kind,
                commit_approved=commit,controls_region=controls,editor_regions=[body,formula])
    if target=='formula':result['formula_region']=list(formula)
    if activation:result['activation_approved']=True
    return result


def save_binding(args, inputs):
    approved=getattr(args,'approve_save',False)
    region=getattr(args,'save_toolbar_region',None)
    if not approved and region is None:return None
    if approved is not True or inputs is None or inputs.get('commit_approved') is not True:
        raise ValueError('save requires explicit input, commit and save approvals')
    if (not isinstance(region,(list,tuple)) or len(region)!=4 or not all(_number(v) for v in region)
            or not 0<=region[0]<region[2] or not 0<=region[1]<region[3]):
        raise ValueError('reviewed save toolbar region required')
    return dict(save_approved=True,destination=workbook_destination(args.run),toolbar_region=list(region))


def credential(path):
    if path.parent.resolve(strict=True) != path.parent:
        raise ValueError('canonical credential parent required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        LeaseGate.private(info)
        if info.st_nlink != 1:
            raise ValueError('private single-link credential required')
        value = stream.read(129).decode('ascii')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', value):
        raise ValueError('bounded credential required')
    return value


def serve(task, server, controller, stopping, *, clock=time.monotonic):
    """No automatic observation/retry. Stop admission before draining handlers."""
    server.timeout = .1
    server.daemon_threads = False
    server.block_on_close = True
    deadline = clock() + 180
    try:
        while not stopping.is_set() and not task.stopped.is_set() and clock() < deadline:
            controller.gate.check()
            server.handle_request()
    finally:
        task.stop()
        try:
            controller.revoke()
        finally:
            try:
                server.server_close()  # Drain accepted handlers before releasing the desktop lock.
            finally:
                task.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'owner', 'session', 'title', 'cell'):
        parser.add_argument('--'+name, required=True)
    for name in ('epoch', 'pid', 'window'):
        parser.add_argument('--'+name, required=True, type=int)
    for name in ('grid', 'name-box-grid'):
        parser.add_argument('--'+name, required=True, type=float, nargs=4)
    parser.add_argument('--approve-selection', action='store_true')
    parser.add_argument('--visual-selection', action='store_true', help='Use fixed offline screenshot recognizer for truncated name-box evidence')
    parser.add_argument('--diagnostic-driver', action='store_true',
                        help='Use the fixed independently deployed diagnostic CLI, original daemon only')
    parser.add_argument('--approve-input',action='store_true')
    parser.add_argument('--approve-window-activation',action='store_true',
                        help='Allow one explicit activation of the bound input window')
    parser.add_argument('--overwrite-disposable',action='store_true')
    parser.add_argument('--approve-commit',action='store_true')
    parser.add_argument('--approve-save',action='store_true')
    parser.add_argument('--save-toolbar-region',type=float,nargs=4)
    parser.add_argument('--input-text')
    parser.add_argument('--input-kind',choices=('text','decimal'))
    parser.add_argument('--input-target',choices=('cell','formula'),default='cell')
    for name in ('input-controls-region','input-body-region','input-formula-region'):
        parser.add_argument('--'+name,type=float,nargs=4)
    parser.add_argument('--approve-cancel-edit', action='store_true')
    parser.add_argument('--pending-edit-text')
    parser.add_argument('--edit-controls-region',type=float,nargs=4)
    parser.add_argument('--edit-body-region',type=float,nargs=4)
    parser.add_argument('--edit-formula-region',type=float,nargs=4)
    parser.add_argument('--controlled', action='store_true',
                        help='Wait for trusted host control; do not require or grant an initial lease')
    args = parser.parse_args(argv)
    if args.diagnostic_driver and not args.controlled:
        parser.error('diagnostic driver requires trusted controlled lifecycle')
    try:
        inputs=input_binding(args)
        saves=save_binding(args,inputs)
    except ValueError as error:parser.error(str(error))
    protocol=CalcSaveModelTask.protocol if saves is not None else CalcInputModelTask.protocol if inputs is not None else PROTOCOL
    edit_fields=(args.pending_edit_text,args.edit_controls_region,args.edit_body_region,args.edit_formula_region)
    if any(v is not None for v in edit_fields) or args.approve_cancel_edit:
        if not args.approve_cancel_edit or any(v is None for v in edit_fields):
            parser.error('explicit disposable edit text and all reviewed regions required')
    if (not args.approve_selection or not re.fullmatch('calc-select-'+UUID, args.run)
            or not re.fullmatch(UUID, args.owner) or not re.fullmatch('session-'+UUID, args.session)
            or args.epoch < 1):
        parser.error('explicit original selection and session binding required')
    require_unlocked()  # VM/account/isolation check before writes or listeners.
    directory = SHARED_LOCK.parent / args.run
    if directory.resolve(strict=True) != directory:
        raise ValueError('existing canonical run required')
    LeaseGate.private(directory.stat(), directory=True)
    controller = LeaseController(directory/'lease.json', run_id=args.run,
                                 owner=args.owner, epoch=args.epoch, clock=time.time)
    model_token = credential(directory/'bridge-token')
    control_token = credential(directory/'control-token')
    if model_token == control_token:
        raise ValueError('independent credentials required')
    if args.controlled:
        return controlled(directory, controller, model_token, control_token, args)
    controller.gate.check()
    # One launch attempt per original run, including failures. Never overwrite.
    _save(directory/'calc-start-intent.json', json.dumps(dict(protocol=protocol,inputBinding=inputs,saveBinding=saves,
          runId=args.run, sessionId=args.session, owner=args.owner, epoch=args.epoch,
          pid=args.pid, window=args.window, title=args.title, cell=args.cell,
          grid=args.grid, nameBoxGrid=args.name_box_grid,**edit_binding(args))).encode())
    task = server = None
    stopping = threading.Event()
    previous = {}
    def interrupted(*_):
        stopping.set()
        if task is not None:
            task.stop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, interrupted)
        factory=CalcSaveModelTask if saves is not None else CalcInputModelTask if inputs is not None else CalcModelTask
        task = factory(directory, lease=controller.gate, pid=args.pid,
            window_id=args.window, title=args.title, cell=args.cell, grid=args.grid,
            session_id=args.session, name_box_grid=args.name_box_grid, approved=True,
            visual_selection=args.visual_selection,
            **edit_binding(args),**(inputs or {}),**(saves or {}))
        server = tools_server(task, model_token, control_token=control_token)
        server.daemon_threads = False
        _save(directory/'calc-ready.json', json.dumps(dict(protocol=protocol,
              runId=args.run, sessionId=args.session, pid=os.getpid(),
              modelUrl='http://192.168.64.3:8766', inputPermitted=False)).encode())
        serve(task, server, controller, stopping)
        return 0
    finally:
        try:
            if task is not None:
                task.stop()
            controller.revoke()
        finally:
            try:
                if server is not None:
                    server.server_close()
                if task is not None:
                    try:
                        task.close()
                    except Exception:
                        quarantine = SHARED_LOCK.with_name(SHARED_LOCK.name+'.quarantine')
                        if not os.path.lexists(quarantine):
                            _save(quarantine, json.dumps(dict(runId=args.run,
                                  reason='CALC_INFLIGHT_REQUIRES_REVIEW')).encode())
                        raise
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)


def controlled(directory, controller, model_token, control_token, args):
    inputs=input_binding(args)
    saves=save_binding(args,inputs)
    protocol=CalcSaveModelTask.protocol if saves is not None else CalcInputModelTask.protocol if inputs is not None else PROTOCOL
    if controller.existing() is not None:
        raise ValueError('controlled launch requires an unused original lease')
    selection = dict(pid=args.pid,window_id=args.window,title=args.title,cell=args.cell,
                     grid=args.grid,session_id=args.session,name_box_grid=args.name_box_grid,**edit_binding(args))
    if getattr(args,'visual_selection',False):selection['visual_selection']=True
    _save(directory/'calc-control-intent.json',json.dumps(dict(runId=args.run,
          sessionId=args.session,selection=selection,inputBinding=inputs,saveBinding=saves,
          diagnosticDriver=diagnostic_cli_binding() if getattr(args,'diagnostic_driver',False) else None)).encode())
    runtime = CalcGuestRuntime(directory,controller,model_token=model_token,
                               control_token=control_token,selection=selection,input_binding=inputs,save_binding=saves,
                               diagnostic_driver=getattr(args,'diagnostic_driver',False))
    server = None
    previous = {}
    stopping = threading.Event()
    def interrupted(*_):
        stopping.set()
        runtime.revoke()
    try:
        for sig in (signal.SIGINT,signal.SIGTERM):
            previous[sig] = signal.signal(sig,interrupted)
        server = control_server(controller,control_token,runtime=runtime)
        server.timeout = .1
        server.daemon_threads = False
        _save(directory/'calc-control-ready.json',json.dumps(dict(
            binding=runtime.status()['binding'],protocol=protocol,sessionId=args.session,
            controlHost='127.0.0.1',controlPort=server.server_port,pid=os.getpid(),
            modelUrl='http://192.168.64.3:8766',activated=False)).encode())
        deadline = time.monotonic()+180
        while not stopping.is_set() and not runtime.closed and time.monotonic()<deadline:
            server.handle_request()
        return 0
    finally:
        try:
            runtime.close()
        finally:
            try:
                if server is not None:
                    server.server_close()
            finally:
                for sig,handler in previous.items():
                    signal.signal(sig,handler)


if __name__ == '__main__':
    raise SystemExit(main())
