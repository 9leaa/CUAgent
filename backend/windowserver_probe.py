"""Isolated read-only macOS SPI study. Never an input authorization gate.

ABI reference: asmvik/yabai dd845723416f5fe92af49fad5ebab00369e07edd,
src/misc/extern.h. Private SPI availability/semantics require VM validation.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import math
import subprocess
import sys
from datetime import datetime, timezone


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def validate(x, y, pid, window):
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (x, y)):
        raise ValueError("INVALID_POINT")
    if type(pid) is not int or not 0 < pid <= 0x7fffffff:
        raise ValueError("INVALID_PID")
    if type(window) is not int or not 0 < window <= 0xffffffff:
        raise ValueError("INVALID_WINDOW")


def query(native, x, y, expected_pid, expected_window):
    validate(x, y, expected_pid, expected_window)
    result = {"version": 1, "status": "UNAVAILABLE", "diagnosticOnly": True,
              "matchesExpected": False, "point": [x, y],
              "expectedPid": expected_pid, "expectedWindow": expected_window,
              "observedAt": datetime.now(timezone.utc).isoformat()}
    connection = native.main()
    result["connection"] = connection
    if connection <= 0:
        result["reason"] = "INVALID_CONNECTION"
        return result
    status, window, owner = native.find(connection, x, y)
    result.update(findStatus=status, window=window, ownerConnection=owner)
    if status != 0 or window <= 0 or window > 0xffffffff or owner <= 0:
        result["reason"] = "WINDOW_QUERY_UNAVAILABLE"
        return result
    # Never skip an overlay/self-owned window to search beneath it.
    status, pid = native.pid(owner)
    result.update(pidStatus=status, pid=pid)
    if status != 0 or pid <= 0 or pid > 0x7fffffff:
        result["reason"] = "OWNER_QUERY_UNAVAILABLE"
        return result
    result.update(status="OBSERVED", matchesExpected=(pid, window) == (expected_pid, expected_window))
    return result


class Native:
    def __init__(self):
        if sys.platform != "darwin":
            raise RuntimeError("MACOS_ONLY")
        self.library = ctypes.CDLL("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight")
        self._main = self.library.SLSMainConnectionID
        self._main.argtypes, self._main.restype = [], ctypes.c_int32
        self._find = self.library.SLSFindWindowAndOwner
        self._find.argtypes = [ctypes.c_int32] * 4 + [ctypes.POINTER(Point)] * 2 + [
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_int32)]
        self._find.restype = ctypes.c_int32
        self._pid = self.library.SLSConnectionGetPID
        self._pid.argtypes = [ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        self._pid.restype = ctypes.c_int32

    def main(self):
        return self._main()

    def find(self, connection, x, y):
        screen, local = Point(x, y), Point(0, 0)
        window, owner = ctypes.c_uint32(0), ctypes.c_int32(0)
        status = self._find(connection, 0, 1, 0, ctypes.byref(screen), ctypes.byref(local),
                            ctypes.byref(window), ctypes.byref(owner))
        return status, window.value, owner.value

    def pid(self, owner):
        pid = ctypes.c_int32(0)
        status = self._pid(owner, ctypes.byref(pid))
        return status, pid.value


def isolated(x, y, pid, window, *, runner=subprocess.run):
    validate(x, y, pid, window)
    command = [sys.executable, "-m", "backend.windowserver_probe", "--worker",
               "--x", str(x), "--y", str(y), "--pid", str(pid), "--window", str(window)]
    try:
        child = runner(command, capture_output=True, timeout=3, check=False)
    except subprocess.TimeoutExpired:
        # subprocess.run kills/reaps its child on timeout. No automatic retry.
        return {"status": "UNKNOWN", "reason": "NATIVE_TIMEOUT", "diagnosticOnly": True,
                "matchesExpected": False}
    if child.returncode != 0 or len(child.stdout) > 8192:
        return {"status": "UNKNOWN", "reason": "CHILD_FAILED", "exitCode": child.returncode,
                "diagnosticOnly": True, "matchesExpected": False}
    try:
        result = json.loads(child.stdout)
        if not isinstance(result, dict) or result.get("diagnosticOnly") is not True:
            raise ValueError("INVALID_RESULT")
        if result.get("status") not in ("OBSERVED", "UNAVAILABLE"):
            raise ValueError("INVALID_STATUS")
        if result["status"] == "OBSERVED":
            validate(x, y, result.get("pid"), result.get("window"))
            if (result.get("expectedPid"), result.get("expectedWindow"), result.get("point")) != (pid, window, [x, y]):
                raise ValueError("WRONG_BINDING")
            if result.get("findStatus") != 0 or result.get("pidStatus") != 0:
                raise ValueError("FAILED_OBSERVATION")
            if result.get("matchesExpected") is not ((result["pid"], result["window"]) == (pid, window)):
                raise ValueError("INCONSISTENT_MATCH")
        elif result.get("matchesExpected") is not False:
            raise ValueError("UNAVAILABLE_CANNOT_MATCH")
        return result
    except (ValueError, UnicodeError):
        return {"status": "UNKNOWN", "reason": "INVALID_CHILD_RESULT", "diagnosticOnly": True,
                "matchesExpected": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    validate(args.x, args.y, args.pid, args.window)
    if args.worker:
        try:
            result = query(Native(), args.x, args.y, args.pid, args.window)
        except (OSError, AttributeError, RuntimeError) as error:
            result = {"status": "UNAVAILABLE", "reason": type(error).__name__,
                      "diagnosticOnly": True, "matchesExpected": False}
    else:
        result = isolated(args.x, args.y, args.pid, args.window)
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
