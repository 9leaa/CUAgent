"""C1 execution policy mocks, not real VM evaluation results."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c1_bridge import C1Task, StopRun

class C1Policy(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.sent=[]
    def tearDown(self):self.tmp.cleanup()
    def task(self,case):
        return C1Task(Path(self.tmp.name)/case,lambda tool,args:self.sent.append((tool,args)) or {'effect':'unverifiable'},
                      lambda _:None,approved=True,case_id=case)
    def snapshot(self,task,label='Submit',role='AXButton',name='s1'):
        task.pid,task.window=1,2
        task.snapshot={'snapshot_id':name,'tree_markdown':'- AXWindow\n  - AXStaticText = "15"',
            'elements':[{'element_index':0,'role':'AXWindow','label':task.case.title},
                        {'element_index':1,'parent_index':0,'role':role,'label':label,
                         'element_token':name+':1','enabled':True,'actions':['AXPress']}]}
        task.observed_at=time.monotonic()
        return {'snapshot_id':name,'element_index':1,'element_token':name+':1'}

    def test_unreviewed_target_and_missing_calculator_source_cannot_dispatch(self):
        task=self.task('cross_app')
        with self.assertRaises(StopRun):task.select_target({'target':'Terminal'})
        with self.assertRaises(StopRun):task.select_target({'target':'CUAgent Transfer'})
        self.assertEqual(self.sent,[])
        self.assertEqual(task.used,0)

    def test_transfer_binds_different_pid_and_requires_new_observation(self):
        task=self.task('cross_app');self.snapshot(task)
        def transport(tool,args):
            self.sent.append((tool,args))
            if tool=='launch_app':return {'bundle_id':'org.cuagent.fixtures','pid':3}
            if tool=='list_windows':return {'windows':[{'pid':3,'window_id':4,'title':'CUAgent Transfer','app_name':'CUAgentFixtures','is_on_screen':True}]}
            return {'effect':'unverifiable'}
        task.transport=transport
        task.select_target({'target':'CUAgent Transfer'})
        self.assertEqual((task.pid,task.window),(3,4))
        self.assertEqual(task.transfer_value,'15')
        self.assertIsNone(task.snapshot)
        with self.assertRaises(StopRun):task.type_text({'snapshot_id':'s1','element_index':1,'element_token':'s1:1','text':'15'})
        args=self.snapshot(task,'Value','AXTextField','s2')
        with self.assertRaises(StopRun):task.type_text({**args,'text':'99'})
        task.type_text({**args,'text':'15'})
        self.assertEqual(self.sent[-1][0],'type_text')
        self.assertEqual(task.used,3)

    def test_controlled_failure_counts_once_and_old_snapshot_cannot_be_retried(self):
        task=self.task('reobserve_failure');args=self.snapshot(task)
        with self.assertRaises(StopRun):task.click(args)
        self.assertEqual(task.used,1)
        self.assertEqual(self.sent,[])
        self.assertIsNone(task.snapshot)
        with self.assertRaises(StopRun):task.click(args)
        task.click(self.snapshot(task,name='s2'))
        self.assertEqual(task.used,2)
        self.assertEqual(len(self.sent),1)
        rows=[json.loads(x) for x in task.ledger.read_text().splitlines()]
        self.assertEqual(sum(x['event']=='controlled_stale_refusal' for x in rows),1)
        self.assertFalse(task.uncertain)

    def test_restart_keeps_budget_and_closed_admission(self):
        task=self.task('input_correction');task.click(self.snapshot(task))
        restored=C1Task(task.directory,lambda *_:None,lambda _:None,approved=True,case_id='input_correction')
        self.assertEqual(restored.used,1)
        self.assertTrue(restored.stopped.is_set())
        with self.assertRaises(StopRun):restored.click(self.snapshot(restored))

    def test_false_popup_success_without_distinct_windows_is_rejected(self):
        task=self.task('popup')
        (task.directory/'c1-effects.json').write_text(json.dumps({'effects':['popup-opened','owned-popup-confirmed']}))
        self.assertFalse(task.verify_ui_trajectory([],['Open Confirmation','Confirm']))
        rows=[{'event':'target_bound','window_id':1},{'event':'target_selected','window_id':2}]
        self.assertTrue(task.verify_ui_trajectory(rows,['Open Confirmation','Confirm']))

    def test_returned_gui_call_is_only_attempt_until_new_effect_observation(self):
        task=self.task('input_correction');task.click(self.snapshot(task))
        rows=[json.loads(x) for x in task.ledger.read_text().splitlines()]
        self.assertTrue(any(x['event']=='attempted_action' for x in rows))
        self.assertFalse(any(x['event']=='completed_action' for x in rows))
        (task.directory/'c1-submission.json').write_text(json.dumps({'value':'cedar-42','submitted':True,'task':'input_correction'}))
        def transport(tool,args):
            if tool=='get_window_state':
                Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\n')
                return {'pid':1,'window_id':2,'app_name':'CUAgentFixtures','window_title':task.case.title,
                        'snapshot_id':'new-effect','screenshot_frame_valid':True,
                        'tree_markdown':'- AXWindow\n  - AXStaticText = "Submitted cedar-42"'}
            return {'effect':'unverifiable'}
        task.transport=transport
        task.observe();task.observe()
        rows=[json.loads(x) for x in task.ledger.read_text().splitlines()]
        completed=[x for x in rows if x['event']=='completed_action']
        self.assertEqual(len(completed),1)
        self.assertEqual(completed[0]['effect_snapshot_id'],'new-effect')

    def test_optional_hint_is_fresh_owned_inventory_not_automatic_action(self):
        with patch.dict('os.environ',{'CUAGENT_C1_OBSERVATION_HINTS':'1'}):task=self.task('popup')
        self.snapshot(task,'Open Confirmation');task.record({'event':'attempted_action','label':'Open Confirmation','snapshot_id':'s0'})
        def transport(tool,args):
            self.sent.append((tool,args))
            return {'windows':[{'pid':1,'app_name':'CUAgentFixtures','title':'CUAgent Confirmation','window_id':3,'is_on_screen':True}]}
        task.transport=transport
        result={'state':task.snapshot}
        task.add_observation_hint(result)
        self.assertEqual(task.used,1)
        self.assertEqual(self.sent,[('list_windows',{'pid':1})])
        self.assertEqual((task.pid,task.window),(1,2))
        self.assertEqual(result['state']['observation_hint']['reviewed_visible_target'],'CUAgent Confirmation')
        self.assertEqual(task.snapshot['snapshot_id'],'s1')
        task.record({'event':'completed_action','label':'Open Confirmation','effect_proven':True})
        task.add_observation_hint(result)
        self.assertEqual(task.used,1)

    def test_hint_default_off_and_foreign_panel_never_promoted(self):
        with patch.dict('os.environ',{'CUAGENT_C1_OBSERVATION_HINTS':'0'}):task=self.task('popup')
        self.snapshot(task,'Open Confirmation');task.record({'event':'attempted_action','label':'Open Confirmation','snapshot_id':'s0'})
        task.add_observation_hint({'state':task.snapshot})
        self.assertEqual(task.used,0)
        task.observation_hints=True
        task.transport=lambda *_:{'windows':[{'pid':9,'app_name':'CUAgentFixtures','title':'CUAgent Confirmation','window_id':3,'is_on_screen':True}]}
        result={'state':task.snapshot};task.add_observation_hint(result)
        self.assertNotIn('observation_hint',result['state'])

if __name__=='__main__':unittest.main()
