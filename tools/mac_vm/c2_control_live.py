"""Developer-only real Driver control diagnostic, not a model/business pass.

This must run in the authorized VM. Does not open a model or control endpoint.
"""
import argparse
import fcntl
import json
from pathlib import Path
import re
from driver_smoke import require_vm, StopRun
from c2_bridge import C2Task

def run(run_id, approved):
    require_vm()
    if not approved or not re.fullmatch(r'c2_control_[A-Za-z0-9_-]{1,60}',run_id):
        raise ValueError('Explicit approval and diagnostic run identity required')
    root=Path.home()/'C0Evidence'
    if root.is_symlink():raise ValueError('Evidence root symlink')
    root.mkdir(mode=0o700,exist_ok=True)
    with (root/'bridge.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        directory=root/run_id
        if directory.exists():raise ValueError('New diagnostic run required; never overwrite evidence')
        task=C2Task(directory,approved=True,case_id='input_correction')
        try:
            initial=task.observe();initial_id=initial['state']['snapshot_id']
            before=task.used
            task.stop()
            try:task.observe()
            except StopRun:pass
            else:raise AssertionError('Stopped task accepted observation')
            assert task.used==before
            task.claim_human();human_epoch=task.epoch
            recovery=task.recovery_observe()
            assert task.used>before and task.snapshot['snapshot_id']!=initial_id
            recovered=task.used
            task.resume('session-c2-developer-diagnostic',human_epoch)
            assert task.snapshot is None and task.used==recovered
            try:task.authorize_session('session-other',task.epoch)
            except StopRun:pass
            else:raise AssertionError('Wrong session accepted')
            task.authorize_session('session-c2-developer-diagnostic',task.epoch)
            final=task.observe()
            assert task.used==recovered+1 and final['state']['snapshot_id']!=recovery['state']['snapshot_id']
            task.stop()
            rows=[json.loads(line) for line in task.ledger.read_text().splitlines()]
            dispatches=[row for row in rows if row['event']=='dispatch']
            assert len(dispatches)==task.used<=30
            assert [row['used'] for row in dispatches]==list(range(1,task.used+1))
            assert not any(row['event']=='UNKNOWN' for row in rows)
            assert not any(row['tool'] not in ('launch_app','list_windows','get_window_state') for row in dispatches)
            report={'gateStatus':'PASS','taskStatus':'UNVERIFIED','scope':'real Driver ownership observations; no model/business execution',
                'run':run_id,'rawCalls':task.used,'beforeTakeover':before,'afterRecovery':recovered,
                'initialSnapshot':initial_id,'recoverySnapshot':recovery['state']['snapshot_id'],
                'finalSnapshot':final['state']['snapshot_id'],'pid':task.pid,'window_id':task.window,
                'epoch':task.epoch,'stopped':task.stopped.is_set()}
            with (directory/'control-diagnostic.json').open('x') as stream:json.dump(report,stream,indent=2)
            print(json.dumps(report))
        finally:
            if not task.stopped.is_set():task.stop()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--approve-task',action='store_true')
    args=parser.parse_args();run(args.run,args.approve_task)
