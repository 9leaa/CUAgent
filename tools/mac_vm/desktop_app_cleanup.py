"""Trusted cleanup coordinator, not a model tool or a production VM entrypoint.

The caller must hold the original desktop lock throughout, supply an identity
captured at launch, and provide independent verification and live OS readers.
Callbacks are trusted dependencies, never task/model supplied capabilities.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import time

from desktop_lease import LeaseGate
from real_app_bridge import EXECUTABLE

UUID_PATTERN = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


@dataclass(frozen=True)
class ApplicationIdentity:
    pid: int
    started_us: int
    executable: str = EXECUTABLE

    def __post_init__(self):
        if (type(self.pid) is not int or self.pid <= 0
                or type(self.started_us) is not int or self.started_us <= 0
                or self.executable != EXECUTABLE):
            raise ValueError('fixed TextEdit process identity required')


@dataclass(frozen=True)
class CleanupState:
    run_id: str
    owner: str
    epoch: int
    terminal: bool
    stopped: bool
    verified: bool
    pending: int
    uncertain: bool
    raw_calls: int


class ApplicationCleanup:
    """At most one graceful request per run, including across object rebuilds."""

    def __init__(self, directory, *, run_id, owner, epoch, application,
                 verified_hashes, read_state, read_identity, read_hashes,
                 request_terminate, clock=time.monotonic, sleep=time.sleep):
        self.directory = Path(directory).absolute()
        if (self.directory.resolve(strict=True) != self.directory
                or self.directory.name != run_id or not isinstance(run_id, str)
                or not re.fullmatch('p2-' + UUID_PATTERN, run_id)
                or not isinstance(owner, str) or not re.fullmatch(UUID_PATTERN, owner)
                or type(epoch) is not int or epoch < 1
                or type(application) is not ApplicationIdentity):
            raise ValueError('bound cleanup identity required')
        LeaseGate.private(self.directory.stat(), directory=True)
        # Only fixed document/result/trace hashes; task-specific independent
        # evidence checking is supplied by the trusted runtime, never the model.
        required = {'document', 'result', 'trace'}
        if (type(verified_hashes) is not dict or set(verified_hashes) != required
                or any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v)
                       for v in verified_hashes.values())):
            raise ValueError('independently verified artifact hashes required')
        for callback in (read_state, read_identity, read_hashes, request_terminate, clock, sleep):
            if not callable(callback):
                raise ValueError('trusted cleanup dependency required')
        self.binding = (run_id, owner, epoch)
        self.application = application
        self.hashes = dict(verified_hashes)
        self.read_state, self.read_identity, self.read_hashes = read_state, read_identity, read_hashes
        self.request_terminate, self.clock, self.sleep = request_terminate, clock, sleep

    def _save(self, name, value):
        # Open a verified directory descriptor so final-component link attacks
        # cannot redirect the persistent no-replay intent or the receipt.
        if self.directory.resolve(strict=True) != self.directory:
            raise ValueError('cleanup directory changed')
        directory = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            LeaseGate.private(os.fstat(directory), directory=True)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(directory)
        finally:
            os.close(directory)

    def _state(self):
        state = self.read_state()
        if (type(state) is not CleanupState
                or (state.run_id, state.owner, state.epoch) != self.binding
                or type(state.epoch) is not int
                or state.terminal is not True or state.stopped is not True
                or state.verified is not True or state.uncertain is not False
                or type(state.pending) is not int or state.pending != 0
                or type(state.raw_calls) is not int or not 0 <= state.raw_calls <= 30):
            raise ValueError('unsafe cleanup state')
        return state

    def _files_match(self):
        return self.read_hashes() == self.hashes

    def run(self):
        run_id, owner, epoch = self.binding
        base = {'version': 1, 'runId': run_id, 'owner': owner, 'epoch': epoch,
                'pid': self.application.pid, 'startedUs': self.application.started_us,
                'executable': self.application.executable, 'verifiedHashes': self.hashes}
        # Write failure propagates. Never terminate without a durable intent.
        self._save('app-cleanup-intent.json', base)
        requested = False
        outcome, reason = 'REFUSED', 'PRECONDITION_FAILED'
        try:
            state = self._state()
            if not self._files_match():
                raise ValueError('artifact drift')
            identity = self.read_identity(self.application.pid)
            if identity is None:
                outcome, reason = 'EXITED', 'ALREADY_ABSENT'
            elif type(identity) is not ApplicationIdentity or identity != self.application:
                reason = 'PROCESS_IDENTITY_CHANGED'
            else:
                # Recheck after potentially slow readers, immediately before
                # the side effect. The OS adapter must itself recheck identity.
                if self._state() != state or not self._files_match():
                    raise ValueError('precondition drift')
                requested = True
                outcome, reason = 'UNKNOWN', 'EXIT_NOT_CONFIRMED'
                accepted = self.request_terminate(self.application)
                if accepted is not True:
                    reason = 'TERMINATION_NOT_ACCEPTED'
                else:
                    deadline = self.clock() + 3
                    for _ in range(13):  # Also bounded if a clock malfunctions.
                        current = self.read_identity(self.application.pid)
                        if current is None:
                            outcome, reason = 'EXITED', 'PROCESS_ABSENT'
                            break
                        if type(current) is not ApplicationIdentity or current != self.application:
                            reason = 'PROCESS_IDENTITY_CHANGED'
                            break
                        remaining = deadline - self.clock()
                        if remaining <= 0:
                            break
                        self.sleep(min(.25, remaining))
            # Cleanup must not alter verified files or the task budget/state.
            if self._state() != state or not self._files_match():
                outcome, reason = 'UNKNOWN', 'POSTCONDITION_CHANGED'
        except Exception:
            # Raw OS/transport exceptions may contain private data. Unknown is
            # preserved after a request, never retried or upgraded to success.
            outcome = 'UNKNOWN' if requested else 'REFUSED'
            reason = 'DEPENDENCY_FAILED' if requested else 'PRECONDITION_FAILED'
        receipt = {**base, 'status': outcome, 'reason': reason,
                   'terminationRequested': requested, 'forced': False}
        self._save('app-cleanup-receipt.json', receipt)
        return receipt
