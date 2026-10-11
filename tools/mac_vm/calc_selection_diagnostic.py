"""Trusted operator-only, bounded stdio entry point for Calc selection.

No lease granting, network listener, model loop, typing or save commands.
Output contains private screenshot/AX evidence; never publish the transcript.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import sys
import time

from calc_selection import CalcSelectionTask
from desktop_lease import LeaseGate
from real_app_bridge import require_unlocked


class BoundedLines:
    """Read bounded bytes with a monotonic deadline, including partial lines."""
    def __init__(self, fd):
        self.fd, self.buffer = fd, bytearray()

    def read(self, deadline):
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('diagnostic deadline')
            newline = self.buffer.find(b'\n')
            if newline >= 0:
                if newline > 4096:
                    raise ValueError('command too large')
                line = bytes(self.buffer[:newline]); del self.buffer[:newline+1]
                return line
            if len(self.buffer) > 4096:
                raise ValueError('command too large')
            ready, _, _ = select.select([self.fd], [], [], min(remaining, 1))
            if not ready:
                continue
            block = os.read(self.fd, min(1024, 4097-len(self.buffer)))
            if not block:
                if self.buffer:
                    raise ValueError('unterminated command')
                return None
            self.buffer.extend(block)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def dispatch(task, line):
    if not isinstance(line, bytes) or len(line) > 4096:
        raise ValueError('bounded byte command required')
    value = json.loads(line.decode('utf8'), object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if not isinstance(value, dict) or not isinstance(value.get('op'), str):
        raise ValueError('command object required')
    op = value['op']
    if op == 'observe' and set(value) == {'op'}:
        return task.observe()
    if op == 'select' and set(value) in ({'op'}, {'op','point'}):
        # Reject explicit null, not silently treat it as an absent coordinate.
        if 'point' in value and not isinstance(value['point'], dict):
            raise ValueError('point object required')
        return task.select(point=value.get('point'))
    if op == 'confirm' and set(value) == {'op','nameBoxIndex'} and type(value['nameBoxIndex']) is int:
        return task.confirm(name_box_index=value['nameBoxIndex'])
    if op == 'stop' and set(value) == {'op'}:
        return task.stop()
    raise ValueError('unapproved diagnostic operation or fields')


def run(task, read_line, emit, *, duration=180, clock=time.monotonic):
    """Own task lifetime; error paths never restart/replay or grant a lease."""
    outcome = 'UNVERIFIED'
    try:
        if not isinstance(duration,(int,float)) or isinstance(duration,bool) or not math.isfinite(duration) or not 0 < duration <= 180:
            raise ValueError('bounded diagnostic duration required')
        deadline = clock()+duration
        emit(dict(event='ready', runId=task.run_id, rawCalls=task.used, businessStatus='UNVERIFIED', inputPermitted=False))
        for _ in range(30):
            if clock() >= deadline:
                raise TimeoutError('diagnostic deadline')
            line = read_line(deadline)
            if line is None:
                break
            if clock() >= deadline:
                raise TimeoutError('diagnostic deadline')
            result = dispatch(task, line)
            emit(dict(event='result', result=result, rawCalls=task.used))
            if clock() >= deadline:
                raise TimeoutError('diagnostic deadline')
            if task.stopped.is_set():
                break
            if task.phase == 'CONFIRMED':
                outcome = 'SELECTION_OBSERVED'
                break
    except Exception as exc:
        emit(dict(event='error', errorType=type(exc).__name__, businessStatus='UNVERIFIED', rawCalls=task.used))
    finally:
        task.close()
    receipt = dict(event='closed', status=outcome, businessStatus='UNVERIFIED', rawCalls=task.used,
                   stopped=task.stopped.is_set(), inputPermitted=False, modelInvoked=False)
    emit(receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--epoch',required=True,type=int)
    parser.add_argument('--lease',required=True,type=Path)
    parser.add_argument('--pid',required=True,type=int)
    parser.add_argument('--window',required=True,type=int)
    parser.add_argument('--title',required=True)
    parser.add_argument('--cell',required=True)
    parser.add_argument('--grid',nargs=4,type=float,required=True)
    parser.add_argument('--approve-selection',action='store_true')
    args=parser.parse_args()
    uuid_pattern=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if (not args.approve_selection or not re.fullmatch('calc-select-'+uuid_pattern,args.run)
            or not re.fullmatch(uuid_pattern,args.owner) or args.epoch<1):
        parser.error('explicit selection approval and canonical diagnostic identities required')
    require_unlocked()
    directory=Path('/Users/mvpagent/C0Evidence')/args.run
    # Lease must be a pre-existing private regular file in this exact run.
    if args.lease != directory/'lease.json' or args.lease.resolve(strict=True) != args.lease:
        raise ValueError('original diagnostic lease path required')
    lease=LeaseGate(args.lease,run_id=args.run,owner=args.owner,epoch=args.epoch)
    task=CalcSelectionTask(directory,lease=lease,pid=args.pid,window_id=args.window,title=args.title,
                           cell=args.cell,grid=args.grid,approved=True)
    def interrupted(*_):
        task.stop()
        raise KeyboardInterrupt
    previous={}
    try:
        for sig in (signal.SIGTERM,signal.SIGINT):
            previous[sig]=signal.signal(sig,interrupted)
        run(task,BoundedLines(sys.stdin.fileno()).read,
            lambda value: print(json.dumps(value,ensure_ascii=False),flush=True))
    finally:
        try:
            task.close()
        finally:
            for sig,handler in previous.items(): signal.signal(sig,handler)


if __name__=='__main__':
    main()
