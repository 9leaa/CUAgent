"""Exact executable identity; never inferred from app/window labels alone."""
import ctypes
import os
from driver_smoke import StopRun
from c0_cases import TASKS

def app_identity(pid, executable):
    if type(pid) is not int or pid<=0 or executable not in {c.executable for c in TASKS.values()}:
        raise StopRun('BLOCKED','Unreviewed app identity')
    lib=ctypes.CDLL('/usr/lib/libproc.dylib')
    lib.proc_pidpath.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32]
    lib.proc_pidpath.restype=ctypes.c_int
    buffer=ctypes.create_string_buffer(4096)
    if lib.proc_pidpath(pid,buffer,len(buffer))<=0 or os.fsdecode(buffer.value)!=executable:
        raise StopRun('BLOCKED','PID no longer belongs to the approved task app')
