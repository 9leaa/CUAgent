"""Calc adapter for the existing trusted lease/control protocol. No self-renewal."""
import json
import os
from pathlib import Path
import re
import threading

from calc_model_task import CalcModelTask
from calc_selection import SHARED_LOCK, _save
from desktop_lease import LeaseGate
from desktop_tools_http import tools_server


class CalcGuestRuntime:
    def __init__(self, directory, controller, *, model_token, control_token, selection,
                 port=8766, loopback_test=False, task_factory=CalcModelTask):
        self.directory = Path(directory).absolute()
        if self.directory.resolve(strict=True) != self.directory or self.directory.name != controller.gate.run_id:
            raise ValueError('original canonical run required')
        LeaseGate.private(self.directory.stat(), directory=True)
        if (type(loopback_test) is not bool or not loopback_test and task_factory is not CalcModelTask
                or not isinstance(selection,dict) or set(selection) !=
                {'pid','window_id','title','cell','grid','session_id','name_box_grid'}):
            raise ValueError('trusted Calc selection required')
        for token in (model_token,control_token):
            if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}',token):
                raise ValueError('private independent tokens required')
        if model_token == control_token:
            raise ValueError('independent credentials required')
        self.controller = controller
        self.model_token, self.control_token = model_token, control_token
        # Freeze caller-owned nested arrays as well as the outer dictionary.
        self.selection = json.loads(json.dumps(selection,allow_nan=False))
        self.port, self.loopback_test, self.factory = port, loopback_test, task_factory
        self.task = self.server = self.thread = None
        self.closed = False
        self.lock = threading.RLock()

    def status(self):
        with self.lock:
            gate = self.controller.gate
            result = dict(binding=dict(version=1,runId=gate.run_id,owner=gate.owner,epoch=gate.epoch),
                active=self.thread is not None and self.thread.is_alive() and not self.closed,
                stopped=self.closed,rawCalls=0,pendingCalls=0,
                modelPort=self.server.server_port if self.server is not None else None)
            lease = self.controller.existing()
            result['stopped'] = self.closed or bool(lease and lease['stopped'])
            if self.task is not None:
                with self.task.dispatch_lock:
                    result.update(stopped=result['stopped'] or self.task.stopped.is_set(),
                                  rawCalls=self.task.used,pendingCalls=len(self.task.inflight))
            return result

    def activate(self):
        with self.lock:
            if self.closed or self.task is not None:
                raise ValueError('Calc activation cannot replay')
            try:
                _save(self.directory/'calc-activation-intent.json',
                      json.dumps(dict(binding=self.status()['binding'],selection=self.selection)).encode())
                self.controller.gate.check()
                self.task = self.factory(self.directory,lease=self.controller.gate,approved=True,**self.selection)
                if not isinstance(self.task,CalcModelTask):
                    raise ValueError('original Calc task required')
                self.controller.gate.check()
                self.server = tools_server(self.task,self.model_token,control_token=self.control_token,
                                          port=self.port,loopback_test=self.loopback_test)
                self.server.daemon_threads = False
                self.server.block_on_close = True
                self.thread = threading.Thread(target=self.server.serve_forever,
                                                kwargs={'poll_interval':.05},daemon=True)
                self.thread.start()
                return self.status()
            except Exception:
                self.revoke()
                if self.server is not None and (self.thread is None or not self.thread.is_alive()):
                    self.server.server_close()
                raise

    def revoke(self):
        # Do not take task.lock: an in-flight GUI call must not delay stop admission.
        with self.lock:
            try:
                return self.controller.revoke()
            finally:
                if self.task is not None:
                    self.task.stop()

    def close(self):
        with self.lock:
            if self.closed:
                return
            try:
                self.revoke()
            finally:
                try:
                    if self.server is not None:
                        if self.thread is not None and self.thread.is_alive():
                            self.server.shutdown()
                        self.server.server_close()  # Drain accepted HTTP handlers before releasing Task lock.
                        if self.thread is not None and self.thread.ident is not None:
                            self.thread.join(3)
                finally:
                    if self.task is not None:
                        try:
                            self.task.close()
                        except Exception:
                            if not self.loopback_test:
                                path = SHARED_LOCK.with_name(SHARED_LOCK.name+'.quarantine')
                                if not os.path.lexists(path):
                                    _save(path,json.dumps(dict(runId=self.controller.gate.run_id,
                                          reason='CALC_INFLIGHT_REQUIRES_REVIEW')).encode())
                            raise
                    self.closed = True

    def _unsupported(self,*_):
        raise ValueError('Calc control does not accept document or handoff operations')

    activate_handoff = provision_handoff = cleanup_application = _unsupported
