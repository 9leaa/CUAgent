"""Document control mocks only, never real GUI/model evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c2_bridge import C2DocumentTask, DOCUMENT_INTERFERENCE, StopRun
from c0_bridge import Task


class DocumentControl(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)/'document-test';self.body='';self.counter=0
        self.task=self.make()

    def make(self):
        with patch.dict('os.environ',{'CUAGENT_C2_FAULT':'manual_document_edit'}):
            return C2DocumentTask(self.directory,self.transport,lambda _:None,approved=True)

    def transport(self,tool,args):
        if tool=='launch_app':return {'pid':11,'bundle_id':'org.cuagent.fixtures'}
        if tool=='list_windows':return {'windows':[{'pid':11,'window_id':12,'title':'CUAgent Document','app_name':'CUAgentFixtures','is_on_screen':True}]}
        if tool=='type_text':self.body=args['text'];return {'effect':'unverifiable'}
        if tool=='set_value':self.body=args['value'];return {'effect':'unverifiable'}
        if tool=='get_window_state':
            self.counter+=1;sid='doc-'+str(self.counter)
            Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\n')
            return {'pid':11,'window_id':12,'app_name':'CUAgentFixtures','window_title':'CUAgent Document',
                    'snapshot_id':sid,'screenshot_frame_valid':True,'tree_markdown':'- AXWindow',
                    'elements':[{'role':'AXWindow','label':'CUAgent Document','element_index':0},
                        {'role':'AXTextArea','label':'Document Body','value':self.body,'element_index':1,
                         'element_token':sid+':1','parent_index':0}]}
        return {}

    def args(self):
        return {'snapshot_id':self.task.snapshot['snapshot_id'],'element_index':1,
                'element_token':self.task.snapshot['snapshot_id']+':1','text':self.task.case.expected}

    def paused_document(self):
        self.task.observe()
        with self.assertRaises(StopRun):self.task.type_text(self.args())
        self.assertEqual((self.task.owner,self.task.used),('paused',4))
        self.task.claim_human();self.task.recovery_observe()

    def test_real_document_backend_bindings_and_control_keep_original_budget(self):
        self.paused_document();self.assertEqual(self.task.body_value(),self.task.case.expected)
        self.task.edit_document();self.assertEqual(self.body,DOCUMENT_INTERFERENCE)
        self.assertEqual(self.task.used,7)
        with self.assertRaises(StopRun):self.task.resume('session-return',self.task.epoch)
        self.task.recovery_observe();self.assertEqual(self.task.used,9)
        self.task.resume('session-return',self.task.epoch)
        self.assertIsNone(self.task.snapshot)
        with self.assertRaises(StopRun):self.task.type_text({'snapshot_id':'old','element_index':1,'element_token':'old:1','text':self.task.case.expected})
        self.task.observe();self.task.type_text(self.args())
        self.assertEqual(self.body,self.task.case.expected)
        restored=self.make();self.assertEqual((restored.pid,restored.window,restored.used),(11,12,11))
        self.assertEqual(restored.owner,'paused');self.assertTrue(restored.fault_injected)

    def test_edit_needs_original_actual_body_and_human_control(self):
        self.task.observe()
        with self.assertRaises(StopRun):self.task.edit_document()
        with self.assertRaises(StopRun):self.task.type_text(self.args())
        self.task.claim_human();self.task.recovery_observe()
        self.task.snapshot['elements'][1]['value']='unexpected'
        with self.assertRaises(StopRun):self.task.edit_document()
        self.assertEqual(self.task.used,6)

    def test_fake_changed_file_without_changed_gui_cannot_resume(self):
        self.paused_document();self.task.edit_document()
        self.body=self.task.case.expected
        self.task.recovery_observe()
        with self.assertRaises(StopRun):self.task.resume('session-return',self.task.epoch)
        self.assertTrue(self.task.stopped.is_set())

    def test_edit_timeout_is_unknown_and_never_auto_resumes(self):
        self.paused_document()
        original=self.task.transport
        def fail(tool,args):
            if tool=='set_value':raise TimeoutError()
            return original(tool,args)
        self.task.transport=fail
        with self.assertRaises(TimeoutError):self.task.edit_document()
        restored=self.make();self.assertTrue(restored.uncertain)
        with self.assertRaises(StopRun):restored.claim_human()

    def test_saved_file_without_full_changed_and_corrected_trajectory_is_false(self):
        expected=self.task.case.expected
        (self.directory/'document-save.json').write_text(json.dumps({'saved':True,'filename':'task-note.txt','text':expected}))
        (self.directory/'task-note.txt').write_text(expected)
        self.assertFalse(self.task.verify_ui_trajectory([],['Save Document','Save']))

    def test_complete_mock_trajectory_requires_changed_gui_after_resume(self):
        self.paused_document();self.task.edit_document();self.task.recovery_observe()
        self.task.resume('session-return',self.task.epoch)
        self.task.observe();self.task.type_text(self.args());self.task.observe()
        expected=self.task.case.expected
        (self.directory/'document-save.json').write_text(json.dumps({'saved':True,'filename':'task-note.txt','text':expected}))
        (self.directory/'task-note.txt').write_text(expected)
        self.task.record({'event':'completed_action','label':'Save Document'})
        self.task.record({'event':'completed_action','label':'Save'})
        rows=[json.loads(x) for x in self.task.ledger.read_text().splitlines()]
        self.assertTrue(self.task.verify_ui_trajectory(rows,['Save Document','Save']))
        resume=next(i for i,r in enumerate(rows) if r['event']=='c2_control' and r.get('reason')=='explicit_resume')
        observation=next(r for r in rows[resume+1:] if r['event']=='result' and r.get('tool')=='get_window_state')
        observation['value']['elements'][1]['value']=expected
        self.assertFalse(self.task.verify_ui_trajectory(rows,['Save Document','Save']))

    def test_document_replacement_is_not_generic_raw_value_access(self):
        self.task.observe()
        with self.assertRaises(StopRun):self.task.raw('set_value',{'pid':11,'window_id':12,'value':'arbitrary'})
        ordinary=Task(Path(self.temp.name)/'ordinary',self.transport,lambda _:None,approved=True)
        with self.assertRaises(StopRun):ordinary.raw('set_value',{'pid':11,'window_id':12,'value':'arbitrary'})
        self.assertEqual(ordinary.used,0)


if __name__=='__main__':unittest.main()
