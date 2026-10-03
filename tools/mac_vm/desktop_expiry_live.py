"""Trusted VM-only lease expiry diagnostic; no model, input, or save requests."""
import argparse
import hashlib
import json
import time

from desktop_control import LeaseController
from desktop_guest import prepare_guest, private_write
from driver_smoke import StopRun


def diagnose(run_id, owner, *, approved=False):
    # prepare_guest checks the ordinary VM identity before any side effect.
    runtime, server = prepare_guest(run_id, owner, 1, approved=approved)
    result = {'runId': run_id, 'owner': owner, 'epoch': 1,
              'scope': 'real-vm-final-admission', 'modelCalls': 0,
              'businessStatus': 'UNVERIFIED', 'verified': False}
    try:
        runtime.controller.renew(1, 20000)
        runtime.activate()
        observed = runtime.task.observe()
        result['snapshotId'] = observed['state']['snapshot_id']
        before = runtime.status()
        if before['stopped'] or before['pendingCalls'] or not 1 <= before['rawCalls'] <= 30:
            raise ValueError('initial real observation unconfirmed')
        result['before'] = before
        lease = runtime.controller.renew(2, 1200)
        result['leaseBeforeExpiry'] = lease
        deadline = time.monotonic() + 5
        while time.time() * 1000 <= lease['expiresAt']:
            if time.monotonic() >= deadline:
                raise ValueError('wall clock expiry unconfirmed')
            time.sleep(.05)
        result['attemptedAtMs'] = int(time.time() * 1000)
        try:
            runtime.task.observe()
        except StopRun:
            result['expiredObservationRejected'] = True
        else:
            raise ValueError('expired observation accepted')
        after = runtime.status()
        result['after'] = after
        if not after['stopped'] or after['pendingCalls'] or after['rawCalls'] != before['rawCalls']:
            raise ValueError('expired execution dispatched or remains unconfirmed')
        for name, controller in (
            ('originalControllerRejected', runtime.controller),
            ('reopenedControllerRejected', LeaseController(
                runtime.controller.path, run_id=run_id, owner=owner, epoch=1, clock=time.time)),
        ):
            try:
                controller.renew(3, 20000)
            except ValueError:
                result[name] = True
            else:
                raise ValueError('expired controller renewed')
        result['leaseAfterExpiry'] = runtime.controller.existing()
        if result['leaseAfterExpiry']['stopped'] is not True:
            raise ValueError('persistent expiry stop unconfirmed')
        result['verified'] = True
    finally:
        try:
            runtime.close()
            result['closed'] = runtime.closed
            result['final'] = runtime.status()
        except Exception:
            result['verified'] = False
            result['closed'] = False
            raise
        finally:
            server.server_close()
            trace = runtime.directory / 'trace.jsonl'
            if trace.exists():
                result['traceSha256'] = hashlib.sha256(trace.read_bytes()).hexdigest()
            private_write(runtime.directory / 'expiry-diagnostic.json', json.dumps(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--approve-task', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = diagnose(args.run, args.owner, approved=args.approve_task)
        print(json.dumps(result))  # No model/control credentials in this summary.
        return 0
    except Exception:
        print('P6_EXPIRY_UNCONFIRMED_REQUIRES_REVIEW')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
