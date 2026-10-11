"""Exact Calc process identity, with only the OS call simulated."""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calc_selection import calc_identity, EXECUTABLE
from driver_smoke import StopRun


@pytest.mark.parametrize('pid',[None, True, 0, -1, '10', 1.5])
def test_invalid_pid_no_os_call(monkeypatch,pid):
    monkeypatch.setattr('calc_selection.ctypes.CDLL',lambda _:pytest.fail('invalid PID reached OS'))
    with pytest.raises(StopRun): calc_identity(pid)


@pytest.mark.parametrize('path,returned,accepted',[(EXECUTABLE,100,True),
    (EXECUTABLE,0,False),('/tmp/soffice',100,False),(EXECUTABLE+'.other',100,False)])
def test_exact_executable(monkeypatch,path,returned,accepted):
    def proc(pid,buffer,size):
        assert pid==10 and size==4096
        buffer.value=path.encode()
        return returned
    def load(path):
        assert path=='/usr/lib/libproc.dylib'
        return SimpleNamespace(proc_pidpath=proc)
    monkeypatch.setattr('calc_selection.ctypes.CDLL',load)
    if accepted: calc_identity(10)
    else:
        with pytest.raises(StopRun): calc_identity(10)
