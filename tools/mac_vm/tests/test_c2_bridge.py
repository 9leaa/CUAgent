"""C2 policy mocks; not real ownership/fault evidence."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c2_bridge import C2Task, StopRun

class C2Control(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.directory=Path(self.tmp.name)/'c2-test';self.sent=[]
        self.task=self.make()
    def tearDown(self):self.tmp.cleanup()
    def make(self):return C2Task(self.directory,self.transport,lambda _:None,approved=True,case_id='input_correction')
    def transport(self,tool,args):
        self.sent.append(tool)
        if tool=='launch_app':return {'bundle_id':'org.cuagent.fixtures','pid':11}
        if tool=='list_windows':return {'windows':[{'pid':11,'window_id':12,'title':'CUAgent Correction','app_name':'CUAgentFixtures','is_on_screen':True}]}
        if tool=='get_window_state':
            Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\n')
            return {'pid':11,'window_id':12,'app_name':'CUAgentFixtures','window_title':'CUAgent Correction',
                'snapshot_id':'snap-'+str(self.task.used),'screenshot_frame_valid':True,
                'tree_markdown':'- AXWindow\n  - AXStaticText = "cedra-42"'}
        return {'effect':'unverifiable'}
    def test_takeover_requires_stop_and_fresh_return_observation(self):
        self.task.observe();self.assertEqual(self.task.used,3)
        with self.assertRaises(StopRun):self.task.claim_human()
        self.task.stop();self.task.claim_human()
        with self.assertRaises(StopRun):self.task.resume('session-new',self.task.epoch)
        self.task.recovery_observe();self.assertEqual(self.task.used,5)
        epoch=self.task.epoch;self.task.resume('session-new',epoch)
        self.assertIsNone(self.task.snapshot)
        self.task.authorize_session('session-new',self.task.epoch)
        with self.assertRaises(StopRun):self.task.authorize_session('session-old',self.task.epoch)
        with self.assertRaises(StopRun):self.task.authorize_session('session-new',epoch)
    def test_recovery_read_capability_never_permits_actions_or_other_threads(self):
        self.task.observe();self.task.stop();self.task.claim_human()
        self.task.recovery_thread=threading.get_ident()
        self.task.recovery_epoch=self.task.epoch
        for tool in ('click','type_text','launch_app','write_result'):
            with self.assertRaises(StopRun):self.task.admit(tool)
        errors=[]
        def worker():
            try:self.task.admit('get_window_state')
            except StopRun:errors.append(True)
        thread=threading.Thread(target=worker);thread.start();thread.join()
        self.assertEqual(errors,[True]);self.assertEqual(self.task.used,3)
    def test_restart_restores_budget_identity_but_never_snapshot_or_admission(self):
        self.task.observe();restored=self.make()
        self.assertEqual((restored.used,restored.pid,restored.window),(3,11,12))
        self.assertTrue(restored.stopped.is_set());self.assertEqual(restored.owner,'paused')
        self.assertIsNone(restored.snapshot)
        with self.assertRaises(StopRun):restored.admit('click')
    def test_unknown_survives_restart_and_observation_does_not_clear_it(self):
        self.task.observe()
        def fail(*_):raise TimeoutError()
        self.task.transport=fail
        with self.assertRaises(TimeoutError):self.task.raw('click',{'pid':11,'window_id':12})
        restored=self.make();self.task=restored
        self.assertTrue(restored.uncertain)
        restored.recovery_observe()
        self.assertTrue(restored.uncertain)
        with self.assertRaises(StopRun):restored.claim_human()
    def test_unfinished_dispatch_and_budget_exhaustion_cannot_reset(self):
        self.task.observe();self.task.admit('click')
        restored=self.make();self.assertTrue(restored.uncertain);self.assertEqual(restored.used,4)
        with self.assertRaises(StopRun):restored.claim_human()
        self.task=restored;restored.used=30
        before=len(self.sent)
        with self.assertRaises(StopRun):restored.recovery_observe()
        self.assertEqual(len(self.sent),before)
    def test_inflight_prevents_control_handoff(self):
        self.task.observe();self.task.admit('get_window_state');self.task.stop()
        with self.assertRaises(StopRun):self.task.claim_human()
        with self.assertRaises(StopRun):self.task.recovery_observe()
    def test_invalid_control_epoch_fails_closed(self):
        self.task.stop()
        self.task.record({'event':'c2_control','policy':'c2-ownership-v1','epoch':99,'owner':'human'})
        with self.assertRaises(StopRun):self.make()
    def test_stop_during_recovery_invalidates_the_observation_capability(self):
        self.task.observe();self.task.stop();self.task.claim_human()
        before=self.task.used
        def transport(tool,args):
            self.task.stop()
            return self.transport(tool,args)
        self.task.transport=transport
        with self.assertRaises(StopRun):self.task.recovery_observe()
        self.assertEqual(self.task.used,before+1)
        self.assertEqual(self.task.owner,'paused')
        self.assertIsNone(self.task.snapshot)
    def test_session_paths_and_bool_epochs_are_not_authorization(self):
        for session in ('session-../other','session-','session-space invalid'):
            with self.assertRaises(StopRun):self.task.authorize_session(session,0)
        with self.assertRaises(StopRun):self.task.authorize_session('session-good',False)
        self.assertEqual(self.task.epoch,0)
    def prepare_unknown_submit(self):
        self.task.observe()
        self.task.record({'event':'completed_input','label':'Code','text':'cedar-42'})
        self.task.pending_intent={'label':'Submit','snapshot_id':self.task.snapshot['snapshot_id'],'pid':11,'window_id':12}
        call=self.task.admit('click');self.task.pending_intent=None
        self.task.record({'event':'UNKNOWN','tool':'click','call_id':call})
        self.task.inflight.remove(call);self.task.uncertain=True;self.task.stop()
        return call
    def actual_submission(self):
        (self.directory/'c1-effects.json').write_text(json.dumps({'effects':['initial-value:cedra-42','corrected-value:cedar-42','submit']}))
        (self.directory/'c1-submission.json').write_text(json.dumps({'value':'cedar-42','submitted':True,'task':'input_correction'}))
        original=self.task.transport
        def observed(tool,args):
            state=original(tool,args)
            if tool=='get_window_state':state['tree_markdown']='- AXWindow\n  - AXStaticText = "Submitted cedar-42"'
            return state
        self.task.transport=observed
    def test_reconciliation_requires_actual_new_status_files_and_full_trajectory(self):
        call=self.prepare_unknown_submit();self.task.recovery_observe()
        with self.assertRaises(StopRun):self.task.reconcile_submit()
        self.actual_submission();self.task.recovery_observe()
        result=self.task.reconcile_submit()
        self.assertEqual(result['reconciled'],call)
        self.assertFalse(self.task.uncertain)
        with self.assertRaises(StopRun):self.task.reconcile_submit()
        restored=self.make();self.assertFalse(restored.uncertain)
        rows=[json.loads(line) for line in self.task.ledger.read_text().splitlines()]
        self.assertEqual(sum(r['event']=='UNKNOWN' for r in rows),1)
        self.assertEqual(sum(r['event']=='completed_action' and r['label']=='Submit' for r in rows),1)
    def test_fake_submission_file_without_matching_fresh_ui_is_not_reconciled(self):
        self.prepare_unknown_submit()
        (self.directory/'c1-effects.json').write_text(json.dumps({'effects':['initial-value:cedra-42','corrected-value:cedar-42','submit']}))
        (self.directory/'c1-submission.json').write_text(json.dumps({'value':'cedar-42','submitted':True,'task':'input_correction'}))
        self.task.recovery_observe()
        with self.assertRaises(StopRun):self.task.reconcile_submit()
        self.assertTrue(self.task.uncertain)
    def test_stale_model_request_cannot_dispatch_after_control_changes(self):
        self.task.observe()
        with self.task.model_request('session-old',0):
            self.task.stop();self.task.claim_human();self.task.recovery_observe()
            self.task.resume('session-new',self.task.epoch)
            with self.assertRaises(StopRun):self.task.admit('click')

    def test_developer_exit_hook_is_once_and_restart_stays_closed(self):
        class SimulatedProcessExit(BaseException):pass
        self.directory=Path(self.tmp.name)/'fresh-exit-test'
        with patch.dict('os.environ',{'CUAGENT_C2_FAULT':'process_exit_after_observe'}):
            self.task=self.make()
            with patch('c2_bridge.os._exit',side_effect=SimulatedProcessExit) as terminate:
                with self.assertRaises(SimulatedProcessExit):self.task.observe()
                terminate.assert_called_once_with(85)
            restored=self.make()
            self.assertEqual((restored.used,restored.pid,restored.window),(3,11,12))
            self.assertTrue(restored.fault_injected)
            self.assertFalse(restored.uncertain)
            self.assertEqual(restored.owner,'paused')
            with self.assertRaises(StopRun):restored.admit('click')

    def test_permission_pause_does_not_simulate_revocation_or_reset_on_restart(self):
        self.directory=Path(self.tmp.name)/'fresh-permission-test'
        with patch.dict('os.environ',{'CUAGENT_C2_FAULT':'permission_revoke_after_observe'}):
            self.task=self.make()
            with self.assertRaises(StopRun):self.task.observe()
            self.assertTrue(self.task.permission_fault_armed)
            self.assertEqual(self.task.owner,'paused')
            self.assertEqual(self.sent,['launch_app','list_windows','get_window_state'])
            rows=[json.loads(line) for line in self.task.ledger.read_text().splitlines()]
            armed=[row for row in rows if row['event']=='c2_permission_fault_armed']
            self.assertEqual(len(armed),1)
            self.assertFalse(armed[0]['permission_changed'])
            self.assertFalse(any(row['event'] in ('error','UNKNOWN') for row in rows))
            self.task=self.make()
            self.assertEqual(self.task.used,3)
            self.task.claim_human();self.task.recovery_observe()
            self.task.resume('session-permission-restored',self.task.epoch)
            self.task.observe()
            self.assertEqual(self.task.used,6)
            self.assertFalse(self.task.stopped.is_set())

    def prepare_window_fault(self):
        self.directory=Path(self.tmp.name)/'fresh-window-test'
        self.window_open=True;self.window_id=12
        def actual(tool,args):
            if tool=='launch_app':
                if not self.window_open:self.window_open=True;self.window_id=13
                return {'bundle_id':'org.cuagent.fixtures','pid':11}
            if tool=='list_windows':return {'windows':[{'pid':11,'window_id':self.window_id,'title':'CUAgent Correction','app_name':'CUAgentFixtures','is_on_screen':True}] if self.window_open else []}
            if tool=='click':self.window_open=False;return {'effect':'unverifiable'}
            value=self.transport(tool,args)
            if tool=='get_window_state':
                value.update(window_id=self.window_id,window_bounds={'x':320,'y':25},elements=[
                    {'role':'AXWindow','label':'CUAgent Correction','element_index':0},
                    {'role':'AXButton','element_index':3,'element_token':'close-token','parent_index':0,
                     'enabled':True,'actions':['AXPress'],'frame':{'x':326,'y':31,'w':16,'h':16}},
                ])
            return value
        with patch.dict('os.environ',{'CUAGENT_C2_FAULT':'window_close_after_observe'}):
            self.task=C2Task(self.directory,actual,lambda _:None,approved=True,case_id='input_correction')
        with self.assertRaises(StopRun):self.task.observe()
        self.assertEqual(self.task.owner,'paused')
        self.task.claim_human();self.task.recovery_observe()

    def test_window_close_reopen_requires_human_fresh_observation_and_same_budget(self):
        self.prepare_window_fault();self.assertEqual(self.task.used,5)
        self.task.close_current_window();self.assertFalse(self.window_open)
        self.assertEqual(self.task.used,7)
        with self.assertRaises(StopRun):self.task.close_current_window()
        with self.assertRaises(StopRun):self.task.resume('session-return',self.task.epoch)
        def reopen(*args,**kwargs):
            self.assertEqual(args[0],['/usr/bin/open','-a','/Users/mvpagent/Applications/CUAgentFixtures.app'])
            self.window_open=True;self.window_id=13
        with patch('c2_bridge.subprocess.run',side_effect=reopen):self.task.reopen_window()
        self.assertEqual(self.task.used,9)
        self.task.recovery_observe();self.assertEqual((self.task.used,self.task.window),(11,13))
        self.task.resume('session-return',self.task.epoch)
        self.assertIsNone(self.task.snapshot)
        with self.assertRaises(StopRun):self.task.close_current_window()

    def test_window_close_button_outside_title_bar_or_ambiguous_is_denied(self):
        self.prepare_window_fault()
        self.task.snapshot['elements'][1]['frame']['x']=500
        with self.assertRaises(StopRun):self.task.close_current_window()
        self.assertEqual(self.task.used,5);self.assertTrue(self.window_open)
        self.task.recovery_observe()
        self.task.snapshot['elements'].append(dict(self.task.snapshot['elements'][1]))
        with self.assertRaises(StopRun):self.task.close_current_window()
        self.assertTrue(self.window_open)

    def test_window_reopen_without_close_or_before_takeover_is_denied(self):
        self.prepare_window_fault()
        with self.assertRaises(StopRun):self.task.reopen_window()
        self.task.stop()
        with self.assertRaises(StopRun):self.task.close_current_window()

    def test_native_reopen_timeout_stays_unknown_across_restart(self):
        self.prepare_window_fault();self.task.close_current_window()
        with patch('c2_bridge.subprocess.run',side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):self.task.reopen_window()
        self.assertTrue(self.task.uncertain);self.assertEqual(self.task.owner,'paused')
        with patch.dict('os.environ',{'CUAGENT_C2_FAULT':'window_close_after_observe'}):
            restored=C2Task(self.directory,self.transport,lambda _:None,approved=True,case_id='input_correction')
        self.assertTrue(restored.uncertain)
        with self.assertRaises(StopRun):restored.claim_human()

if __name__=='__main__':unittest.main()
