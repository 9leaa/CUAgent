"""Read-only developer inventory. Never starts a VM or calls desktop tools."""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Inspection failed: " + args[0])
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--vm", default="mac-agent-mvp-15-6-1")
    parser.add_argument("--lume", type=Path, default=Path.home() / ".local/bin/lume")
    args = parser.parse_args()
    storage = args.storage.resolve(strict=True)
    report = {
        "purpose": "developer-only read-only inventory; not an Agent tool",
        "macos": command(["/usr/bin/sw_vers", "-productVersion"]),
        "chip": command(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"]),
        "memory_bytes": int(command(["/usr/sbin/sysctl", "-n", "hw.memsize"])),
        "free_disk_bytes": shutil.disk_usage(storage).free,
        "lume_version": command([str(args.lume), "--version"]),
        "storage": str(storage),
        "vm_name": args.vm,
        "m0_acceptance": "NOT_ASSESSED",
    }
    output = command([
        str(args.lume), "get", args.vm, "--storage", str(storage), "--format", "json"
    ])
    # Lume may emit stale-session cleanup logs before its JSON array.
    # Parse only the final array; never print the unfiltered credential-bearing output.
    candidates = []
    for match in re.finditer(r"(?m)^\s*\[", output):
        try:
            candidates.append(json.loads(output[match.start():]))
        except json.JSONDecodeError:
            pass
    if len(candidates) != 1:
        raise RuntimeError("Expected one complete Lume JSON array")
    details = candidates[0]
    if not isinstance(details, list) or len(details) != 1:
        raise RuntimeError("Expected exactly one VM")
    # Never serialize VNC credentials, machine identifiers or arbitrary config fields.
    report["vm"] = {key: details[0].get(key) for key in (
        "status", "provisioningOperation", "os", "cpuCount", "memorySize",
        "diskSize", "display", "networkMode",
    )}
    report["isolation"] = {
        "runtime_verified": False,
        "verification_scope": "inventory only; does not inspect a running hypervisor",
        "reason": (
            "Lume 0.5.3 source adds implicit lume-config and /var/empty shares; "
            "native display enables clipboard sync. CLI sharedDirectories=null "
            "does not prove absence of host directory devices. The project-local "
            "opt-in isolation patch has separate test and boot evidence; this "
            "inventory cannot certify that a VM was launched with that patch."
        ),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
