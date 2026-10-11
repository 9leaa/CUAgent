"""Bounded operator protocol with original executor and simulated Driver."""
import json
import os
import time

import pytest

from test_calc_selection import setup, state, point
from calc_selection_diagnostic import BoundedLines, run


@pytest.mark.parametrize('ax', [True, False])
def test_complete_selection(setup, ax):
    task, calls, snapshot, *_ = setup
    snapshot['elements_complete'] = ax
    commands = iter(['observe', 'select', 'confirm'] if ax else ['observe','select','select','confirm'])
    selections = [0]
    def read(_):
        op = next(commands)
        command = dict(op=op)
        if op == 'select' and not ax:
            selections[0] += 1
            if selections[0] == 2:
                command['point'] = point(task)
        if op == 'confirm': command['nameBoxIndex'] = 2
        return json.dumps(command).encode()
    events = []
    result = run(task, read, events.append)
    assert result['status'] == 'SELECTION_OBSERVED'
    assert result['businessStatus'] == 'UNVERIFIED'
    assert result['stopped'] and not result['inputPermitted']
    assert not result['modelInvoked'] and result['rawCalls'] == 3
    assert [name for name, _ in calls] == ['get_window_state','click','get_window_state']


@pytest.mark.parametrize('line', [b'{"op":"type_text"}', b'{"op":"observe","pid":1}',
    b'{"op":"observe","op":"stop"}', b'{"op":"select","point":null}',
    b'{"op":"confirm","nameBoxIndex":true}', b'{"op":"select","point":{"x":NaN}}',
    b'[]', b'\xff', b'x'*4097, 'not bytes'])
def test_invalid_commands_stop_without_driver(setup, line):
    task, calls, *_ = setup
    events = []
    result = run(task, lambda _:line, events.append)
    assert result['status'] == 'UNVERIFIED' and result['stopped']
    assert not calls and any(event['event']=='error' for event in events)


@pytest.mark.parametrize('mode', ['eof','timeout','interrupt','writer','invalid_duration'])
def test_cleanup(setup, mode):
    task, calls, *_ = setup
    def read(_):
        if mode == 'timeout': raise TimeoutError('private detail')
        if mode == 'interrupt': raise KeyboardInterrupt
        return None
    def emit(_):
        if mode == 'writer': raise BrokenPipeError
    if mode in ('interrupt','writer'):
        with pytest.raises(KeyboardInterrupt if mode=='interrupt' else BrokenPipeError):
            run(task, read, emit)
    else:
        run(task, read, emit, duration=False if mode=='invalid_duration' else 180)
    assert task.stopped.is_set() and not calls


def test_deadline_after_read_no_dispatch(setup):
    task, calls, *_ = setup
    now = [0]
    def read(_):
        now[0] = 181
        return b'{"op":"observe"}'
    run(task, read, lambda _:None, clock=lambda:now[0])
    assert task.stopped.is_set() and not calls


def test_bounded_local_commands(setup):
    task, calls, *_ = setup
    commands = iter([b'{"op":"observe"}']+[b'{"op":"select"}']*29)
    result = run(task, lambda _:next(commands), lambda _:None)
    assert result['status']=='UNVERIFIED' and result['rawCalls']==1
    assert len(calls)==1 and task.stopped.is_set()


@pytest.mark.parametrize('payload,expected', [(b'a\nb\n',[b'a',b'b',None]),
    (b'x'*4096+b'\n',[b'x'*4096,None]), (b'', [None])])
def test_line_reader(payload, expected):
    reader, writer = os.pipe()
    try:
        os.write(writer,payload); os.close(writer); writer=None
        stream = BoundedLines(reader)
        assert [stream.read(time.monotonic()+1) for _ in expected] == expected
    finally:
        os.close(reader)
        if writer is not None: os.close(writer)


@pytest.mark.parametrize('payload',[b'partial',b'x'*4097+b'\n'])
def test_line_reader_rejects(payload):
    reader, writer = os.pipe()
    try:
        os.write(writer,payload); os.close(writer)
        with pytest.raises(ValueError): BoundedLines(reader).read(time.monotonic()+1)
    finally: os.close(reader)


def test_line_deadline():
    reader, writer = os.pipe()
    try:
        with pytest.raises(TimeoutError): BoundedLines(reader).read(time.monotonic()-1)
    finally:
        os.close(reader); os.close(writer)
