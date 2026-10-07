"""Opt-in P7 material reader. Not registered in the production P6 protocol."""
import hashlib
import json
import math
import os
import re
import stat
import time

from desktop_lease import DesktopTask, LeaseGate
from driver_smoke import StopRun
from real_app_bridge import body_from_state


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate material key')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('nonfinite material number')


def close_target(state):
    """Bound native title-bar control; never infer a pixel click or menu action."""
    elements = state.get('elements', [])
    bounds = state.get('window_bounds', {})
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)
    roots = [e for e in elements if e.get('role') == 'AXWindow'
             and e.get('label') == state.get('window_title')]
    if (state.get('screenshot_frame_valid') is not True or len(roots) != 1
            or any(e.get('role') in ('AXSheet', 'AXDialog') for e in elements)
            or not all(finite(bounds.get(k)) for k in ('x', 'y'))):
        raise StopRun('UNVERIFIED', 'Fresh unique close control required')
    candidates = []
    for e in elements:
        frame = e.get('frame', {})
        if (e.get('role') == 'AXButton' and not e.get('label') and e.get('enabled') is True
                and e.get('parent_index') == roots[0].get('element_index')
                and 'AXPress' in e.get('actions', [])
                and all(finite(frame.get(k)) for k in ('x', 'y', 'w', 'h'))
                and 0 < frame['w'] <= 22 and 0 < frame['h'] <= 22
                and 0 <= frame['x'] - bounds['x'] <= 12
                and 0 <= frame['y'] - bounds['y'] <= 12):
            candidates.append(e)
    if len(candidates) != 1:
        raise StopRun('UNVERIFIED', 'Ambiguous or missing close control')
    button = candidates[0]
    index, token = button.get('element_index'), button.get('element_token')
    if (type(index) is not int or index < 0 or type(token) is not str
            or token != f"{state.get('snapshot_id')}:{index}"
            or sum(e.get('element_index') == index or e.get('element_token') == token for e in elements) != 1):
        raise StopRun('UNVERIFIED', 'Invalid close control identity')
    return dict(element_index=index, element_token=token)


class HandoffDesktopTask(DesktopTask):
    def __init__(self, *args, input_sha256, document_opener=None, draft_session_id=None, **kwargs):
        # Trusted constructor binding, never accepted from model tool arguments.
        if not isinstance(input_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', input_sha256):
            raise ValueError('frozen input digest required')
        self.input_sha256 = input_sha256
        if draft_session_id is not None and (type(draft_session_id) is not str or not re.fullmatch(
                r'session-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',draft_session_id)):
            raise ValueError('trusted draft session required')
        self.draft_session_id = draft_session_id
        self.validated_draft = None
        if document_opener is not None and not callable(document_opener):
            raise ValueError('trusted document opener required')
        self.document_opener = document_opener
        self.reopen_phase = None
        self.reopened = False
        self.saved_once = False
        self.input_once = False
        self.close_args = None
        super().__init__(*args, **kwargs)

    def type_text(self, args):
        with self.lock:
            if self.reopen_phase is not None:
                raise StopRun('BLOCKED', 'Editing after reopen intent denied')
            if self.draft_session_id is not None:
                if (self.input_once or self.validated_draft is None or type(args) is not dict
                        or args.get('text') != self.validated_draft['document']):
                    raise StopRun('BLOCKED', 'Original validated draft body required')
            result = super().type_text(args)
            self.input_once = True
            return result

    def save(self, args):
        with self.lock:
            if self.reopen_phase is not None:
                raise StopRun('BLOCKED', 'Saving after reopen intent denied')
            if self.draft_session_id is not None:
                if not self.input_once or self.validated_draft is None or not self.snapshot:
                    raise StopRun('BLOCKED', 'Observed original draft required before save')
                body = body_from_state(self.snapshot)
                if self.validated_draft['document'] not in (body, body + '\n'):
                    raise StopRun('BLOCKED', 'Observed body differs from validated draft')
            value = super().save(args)
            self.saved_once = True
            return value

    def validate_raw(self, tool, args):
        if tool == 'click':
            self.environment()
            if self.reopen_phase != 'closing' or self.close_args is None or args != self.close_args or self.pid is None:
                raise StopRun('BLOCKED', 'Only original task window close permitted')
            self.identity(self.pid)
            return
        return super().validate_raw(tool, args)

    def _saved_bytes(self):
        if self.document.resolve(strict=True) != self.document or self.document.parent.resolve(strict=True) != self.document.parent:
            raise StopRun('BLOCKED', 'Original document path changed')
        fd = os.open(self.document, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                    or not 0 < info.st_size <= 4096):
                raise StopRun('BLOCKED', 'Saved task document required')
            data = stream.read(4097)
        if not 0 < len(data) <= 4096:
            raise StopRun('BLOCKED', 'Saved task document size invalid')
        return data

    def _windows_after(self, old, opening):
        for attempt in range(3):
            value = self.raw('list_windows', {'pid': self.pid})
            windows = value.get('windows')
            if not isinstance(windows, list) or any(not isinstance(w, dict) or type(w.get('pid')) is not int
                    or type(w.get('window_id')) is not int or w['window_id'] <= 0
                    or type(w.get('is_on_screen')) is not bool or not isinstance(w.get('title'), str)
                    or not isinstance(w.get('app_name'), str) for w in windows):
                raise StopRun('UNVERIFIED', 'Invalid reopen window inventory')
            if not opening:
                if not any(w['pid'] == self.pid and (w['window_id'] == old or w['title'] == self.case.title) for w in windows):
                    return None
            else:
                matches = [w for w in windows if w['pid'] == self.pid and w['title'] == self.case.title
                           and w['app_name'] == self.case.app_name and w['is_on_screen']]
                if len(matches) > 1:
                    raise StopRun('UNVERIFIED', 'Ambiguous reopened task window')
                if len(matches) == 1:
                    return matches[0]['window_id']
            if attempt < 2: time.sleep(.1)
        raise StopRun('UNVERIFIED', 'Reopen window transition not confirmed')

    def reopen(self, args):
        with self.lock:
            state = self.snapshot
            if (type(args) is not dict or set(args) != {'snapshot_id'} or not state
                    or args['snapshot_id'] != state['snapshot_id'] or time.monotonic() - self.observed_at > 30
                    or state.get('pid') != self.pid or state.get('window_id') != self.window
                    or state.get('window_title') != self.case.title or state.get('app_name') != self.case.app_name
                    or self.reopen_phase is not None or not self.saved_once or self.document_opener is None
                    or self.used > 19):
                raise StopRun('BLOCKED', 'Saved fresh original window and eleven remaining calls required')
            self.lease.check()
            if self.stopped.is_set() or self.uncertain or self.inflight:
                raise StopRun('BLOCKED', 'Idle authorized task required')
            original = self._saved_bytes()
            if original != self.observed_value().encode('utf-8'):
                raise StopRun('UNVERIFIED', 'Saved body changed')
            self.reopen_digest = hashlib.sha256(original).hexdigest()
            old = self.window
            button = close_target(state)
            intent = dict(snapshot_id=args['snapshot_id'], pid=self.pid, window_id=old, sha256=self.reopen_digest, **button)
            fd = os.open(self.directory / 'handoff-reopen-intent.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as stream:
                json.dump(intent, stream); stream.flush(); os.fsync(stream.fileno())
            parent = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try: os.fsync(parent)
            finally: os.close(parent)
            self.reopen_phase = 'closing'
            self.snapshot = None
            try:
                self.record({'event': 'handoff_reopen_intent', **intent})
                self.close_args = dict(pid=self.pid, window_id=old, session=self.run_id, **button)
                try:
                    self.raw('click', self.close_args)
                finally:
                    self.close_args = None
                self._windows_after(old, False)
                self.record({'event': 'handoff_window_closed', 'pid': self.pid, 'window_id': old})
                self.reopen_phase = 'opening'
                self.environment(); self.identity(self.pid)
                if self._saved_bytes() != original:
                    raise StopRun('UNVERIFIED', 'Document changed during close')
                call = self.admit('reopen_document')
                try:
                    if self.document_opener(self.pid, self.document) is not True:
                        raise ValueError('open acknowledgement missing')
                    self.record({'event': 'result', 'tool': 'reopen_document', 'call_id': call,
                                 'value': {'requested': True, 'pid': self.pid, 'documentSha256': self.reopen_digest}})
                except Exception as error:
                    self.uncertain = True
                    from desktop_app_native import NativeRequestError
                    detail = {}
                    if type(error) is NativeRequestError:
                        # Revalidate the mutable attribute before writing a trace.
                        try:
                            checked = NativeRequestError(**error.diagnostic)
                            detail['nativeDiagnostic'] = checked.diagnostic
                        except (TypeError, ValueError):
                            pass
                    self.record({'event': 'UNKNOWN', 'tool': 'reopen_document', 'call_id': call,
                                 'error': type(error).__name__, **detail})
                    raise
                finally:
                    with self.dispatch_lock: self.inflight.discard(call)
                self.window = self._windows_after(old, True)
                if self._saved_bytes() != original:
                    raise StopRun('UNVERIFIED', 'Document changed while reopening')
                self.reopened = True
                self.reopen_phase = 'reopened'
                self.record({'event': 'handoff_window_reopened', 'pid': self.pid, 'window_id': self.window,
                             'old_window_id': old, 'sha256': self.reopen_digest, 'used': self.used})
                return {'requires_new_observation': True, 'used': self.used}
            except Exception:
                self.stop()
                raise

    def write_result(self, args):
        if not self.reopened or hashlib.sha256(self._saved_bytes()).hexdigest() != self.reopen_digest:
            raise StopRun('UNVERIFIED', 'Unchanged reopened document required before result')
        return super().write_result(args)

    def locate_quote(self, args):
        """Not exposed by HTTP yet: future protocol must verify this exchange."""
        from handoff_quote import locate
        with self.lock:
            self.snapshot = None
            with self.dispatch_lock:
                call_id = self.admit('locate_quote')
            try:
                if self.reopen_phase is not None:
                    raise StopRun('BLOCKED', 'Quote lookup after reopen denied')
                value = locate(self._read_frozen_input(), args)
                # locate validates and bounds args before writing them to audit.
                response = dict(value, inputSha256=self.input_sha256, used=self.used)
                self.record(dict(event='helper_arguments', tool='locate_quote',
                                 call_id=call_id, args=dict(args)))
                self.record(dict(event='result', tool='locate_quote',
                                 call_id=call_id, value=response))
                return response
            except Exception as error:
                self.record(dict(event='error', tool='locate_quote', call_id=call_id,
                                 error=type(error).__name__))
                raise
            finally:
                with self.dispatch_lock:
                    self.inflight.discard(call_id)

    def check_draft(self, args):
        """Identity comes only from trusted activation, never model arguments."""
        from handoff_draft import check
        with self.lock:
            self.snapshot = None
            with self.dispatch_lock:
                call_id = self.admit('check_draft')
            self.validated_draft = None
            try:
                if self.draft_session_id is None or self.reopen_phase is not None or self.saved_once or self.input_once:
                    raise StopRun('BLOCKED', 'Bound pre-save draft required')
                if (type(args) is not dict or set(args) != {'raw'} or type(args['raw']) is not str
                        or not 0 < len(args['raw'].encode()) <= 65536):
                    raise ValueError('bounded draft arguments required')
                result = check(self._read_frozen_input(),args['raw'],run_id=self.directory.name,
                               session_id=self.draft_session_id)
                response = dict(result,inputSha256=self.input_sha256,used=self.used)
                self.record(dict(event='helper_arguments',tool='check_draft',call_id=call_id,args=dict(args)))
                self.record(dict(event='result',tool='check_draft',call_id=call_id,value=response))
                if result['status']=='DRAFT_STRUCTURE_VALID': self.validated_draft = dict(result)
                return response
            except Exception as error:
                self.record(dict(event='error',tool='check_draft',call_id=call_id,error=type(error).__name__))
                raise
            finally:
                with self.dispatch_lock: self.inflight.discard(call_id)

    def read_materials(self):
        with self.lock:
            self.snapshot = None
            with self.dispatch_lock:
                call_id = self.admit('read_materials')
            try:
                value = self._read_frozen_input()
                self.record({'event': 'result', 'tool': 'read_materials', 'call_id': call_id,
                             'value': value, 'inputSha256': self.input_sha256})
                return {'materials': value, 'inputSha256': self.input_sha256, 'used': self.used}
            except Exception as exc:
                self.record({'event': 'error', 'tool': 'read_materials', 'call_id': call_id,
                             'error': type(exc).__name__})
                raise
            finally:
                with self.dispatch_lock:
                    self.inflight.discard(call_id)

    def _read_frozen_input(self):
        directory = self.directory.absolute()
        if directory.resolve(strict=True) != directory:
            raise StopRun('BLOCKED', 'canonical material directory required')
        root = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(root)
            LeaseGate.private(info, directory=True)
            current = directory.stat(follow_symlinks=False)
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise StopRun('BLOCKED', 'material directory changed')
            fd = os.open('handoff-input.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                LeaseGate.private(info)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 < info.st_size <= 256 * 1024:
                    raise StopRun('BLOCKED', 'bounded private material file required')
                raw = stream.read(256 * 1024 + 1)
        finally:
            os.close(root)
        if len(raw) > 256 * 1024 or hashlib.sha256(raw).hexdigest() != self.input_sha256:
            raise StopRun('UNVERIFIED', 'material bytes differ from trusted input')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
        if (type(value) is not dict or set(value) != {'kind', 'project', 'asOf', 'notes', 'tasksCsv', 'previousReport'}
                or value['kind'] != 'project-handoff'):
            raise StopRun('BLOCKED', 'project handoff input required')
        return value
