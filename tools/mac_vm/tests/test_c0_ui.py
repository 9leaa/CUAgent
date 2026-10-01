"""UI policy/verification mocks; not GUI or model evidence."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c0_bridge import Task, StopRun

class UI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.sent=[]
    def tearDown(self): self.tmp.cleanup()
    def task(self, case):
        return Task(Path(self.tmp.name)/case,lambda tool,args:self.sent.append((tool,args)) or {'ok':True},lambda _:None,approved=True,case_id=case)
    def snapshot(self,task,role,label):
        task.pid,task.window=1,2
        task.snapshot={'snapshot_id':'s','elements':[
            {'element_index':0,'role':'AXWindow','label':task.case.title},
            {'element_index':1,'parent_index':0,'role':role,'label':label,'element_token':'t','enabled':True,'actions':['AXPress']}]}
        task.observed_at=time.monotonic()
        return {'snapshot_id':'s','element_index':1,'element_token':'t'}
    def test_form_exact_input_and_window_scope(self):
        task=self.task('form');args=self.snapshot(task,'AXTextField','Code')
        with self.assertRaises(StopRun):task.type_text({**args,'text':'private data'})
        task.snapshot['elements'][1]['parent_index']=None
        with self.assertRaises(StopRun):task.type_text({**args,'text':'cedar-42'})
        args=self.snapshot(task,'AXTextField','Code');task.type_text({**args,'text':'cedar-42'})
        self.assertEqual(self.sent[0][0],'type_text')
        with self.assertRaises(StopRun):task.type_text({**args,'text':'cedar-42'})
    def test_scroll_scope_and_range(self):
        task=self.task('scroll');self.snapshot(task,'AXScrollArea','Task Scroll Area')
        task.snapshot.update(screenshot_frame_valid=True,screenshot_scale=2,window_bounds={'width':640,'height':508})
        args={'snapshot_id':'s','x':640,'y':500}
        for amount in (0,11,True):
            with self.assertRaises(StopRun):task.scroll({**args,'direction':'down','amount':amount})
        task.scroll({**args,'direction':'down','amount':3})
        self.assertEqual(self.sent[0][1]['by'],'page')
        with self.assertRaises(StopRun):self.task('form').scroll({**args,'direction':'down','amount':3})

    def test_rejected_reviewed_requests_consume_budget_and_stop_at_limit(self):
        task=self.task('form')
        for n in range(30):task.charge_rejection('type_text',n,'bad field')
        self.assertEqual(task.used,30)
        task.charge_rejection('type_text',30,'bad field')
        self.assertEqual(task.used,30)
        with self.assertRaises(StopRun):task.admit('get_window_state')

    def test_pixel_scroll_rejects_points_outside_viewport_and_stale_frame(self):
        task=self.task('scroll');self.snapshot(task,'AXScrollArea','Task Scroll Area')
        args={'snapshot_id':'s','x':0,'y':0,'direction':'down','amount':3}
        with self.assertRaises(StopRun):task.scroll(args)
        task.snapshot.update(screenshot_frame_valid=True,screenshot_scale=2,window_bounds={'width':640,'height':508})
        with self.assertRaises(StopRun):task.scroll(args)
        task.snapshot['window_bounds']['width']=700
        with self.assertRaises(StopRun):task.scroll({**args,'x':600,'y':400})
    def test_gui_artifact_not_sufficient_without_trajectory_and_fresh_ui(self):
        task=self.task('document');self.snapshot(task,'AXTextArea','Document Body')
        (task.directory/'task-note.txt').write_text(task.case.expected)
        (task.directory/'document-save.json').write_text(json.dumps({'saved':True,'filename':'task-note.txt','text':task.case.expected}))
        task.snapshot['tree_markdown']='- AXWindow\n  - AXStaticText = "Not completed"'
        with self.assertRaises(StopRun):task.observed_value()
        task.snapshot['tree_markdown']='- AXWindow\n  - AXStaticText = "Saved task-note.txt"'
        task.write_result({'snapshot_id':'s','value':task.case.expected});task.read_result()
        with patch.object(task,'observe'):
            self.assertEqual(task.verify()['status'],'UNVERIFIED')
            task.record({'event':'completed_input','label':'Document Body','text':task.case.expected})
            for label in ('Save Document','Save'):task.record({'event':'completed_action','label':label})
            self.assertEqual(task.verify()['status'],'SUCCEEDED')
    def test_scroll_must_move_and_target_must_really_be_visible(self):
        task=self.task('scroll');self.snapshot(task,'AXScrollArea','Task Scroll Area')
        task.snapshot['tree_markdown']='- AXWindow\n  - AXStaticText = "TARGET: harbor-729"\n  - AXStaticText = "TARGET visible"'
        path=task.directory/'viewport.json'
        path.write_text(json.dumps({'targetVisible':False,'originY':0,'target':'harbor-729'}))
        with self.assertRaises(StopRun):task.observed_value()
        path.write_text(json.dumps({'targetVisible':True,'originY':2000,'target':'harbor-729'}))
        self.assertFalse(task.verify_ui_trajectory([],[]))
        self.assertTrue(task.verify_ui_trajectory([{'event':'completed_scroll'}],[]))
    def test_gui_symlink_refused_and_other_bundle_refused(self):
        task=self.task('form')
        with self.assertRaises(StopRun):task.raw('launch_app',{'bundle_id':'com.apple.Terminal'})
        (task.directory/'submission.json').symlink_to(Path(self.tmp.name)/'outside')
        with self.assertRaises(StopRun):task.task_file('submission.json')

    def test_save_panel_confirmation_is_owned_bounded_and_audited(self):
        task=self.task('document');args=self.snapshot(task,'AXButton','Save')
        task.snapshot.update(screenshot_frame_valid=True,screenshot_scale=2,window_bounds={'x':50,'y':25,'width':640,'height':508})
        task.snapshot['elements'][1]['frame']={'x':450,'y':230,'w':40,'h':20}
        bounds={'x':100,'y':100,'width':430,'height':167}
        def transport(tool,values):
            self.sent.append((tool,values))
            if tool=='list_windows':return {'windows':[{'pid':1,'app_name':'CUAgentFixtures','title':'Save task document','is_on_screen':True,'window_id':3,'bounds':bounds}]}
            if tool=='get_window_state':return {'pid':1,'window_id':3,'app_name':'CUAgentFixtures','window_title':'Save task document','screenshot_frame_valid':True,'screenshot_scale':2,'window_bounds':bounds}
            return {'effect':'unverifiable'}
        task.transport=transport
        task.click(args)
        self.assertEqual(task.window,2)
        values=self.sent[-1][1]
        self.assertEqual(self.sent[-1][0],'press_key')
        self.assertEqual(values, {'pid':1,'window_id':3,'session':'document','key':'return','delivery_mode':'foreground'})
        self.assertFalse(task.save_confirmation_pending)
        with self.assertRaises(StopRun):task.raw('press_key',values)
        rows=[json.loads(x) for x in task.ledger.read_text().splitlines()]
        self.assertEqual(sum(r['event']=='dispatch' for r in rows),2)
        self.assertTrue(any(r['event']=='save_panel_grounding' for r in rows))
        self.assertFalse(any(r['event']=='completed_action' and r.get('label')=='Save' for r in rows))
        original_transport=task.transport
        def unresolved_transport(tool,values):
            result=original_transport(tool,values)
            if tool=='get_window_state':result['degraded_reason']='ax_window_unresolved: owned sheet'
            return result
        task.transport=unresolved_transport
        args=self.snapshot(task,'AXButton','Save')
        task.snapshot.update(screenshot_frame_valid=True,screenshot_scale=2,window_bounds={'x':50,'y':25,'width':640,'height':508})
        task.snapshot['elements'][1]['frame']={'x':450,'y':230,'w':40,'h':20}
        task.click(args)
        self.assertEqual(self.sent[-1][1]['delivery_mode'],'foreground')
        self.assertEqual(self.sent[-1][1]['window_id'],3)
        self.assertEqual(task.window,2)
        (task.directory/'task-note.txt').write_text(task.case.expected)
        def saved_transport(tool,values):
            if tool=='get_window_state':
                Path(values['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\n')
                return {'pid':1,'window_id':2,'app_name':task.case.app_name,'window_title':task.case.title,
                        'snapshot_id':'saved-fresh','screenshot_frame_valid':True,'tree_markdown':'- AXWindow\n  - AXStaticText = "Saved task-note.txt"'}
            return original_transport(tool,values)
        task.transport=saved_transport
        task.observe()
        task.observe()
        rows=[json.loads(x) for x in task.ledger.read_text().splitlines()]
        saves=[r for r in rows if r['event']=='completed_action' and r.get('label')=='Save']
        self.assertEqual(len(saves),1)
        self.assertEqual(saves[0]['effect_snapshot_id'],'saved-fresh')
        args=self.snapshot(task,'AXButton','Save')
        task.snapshot.update(screenshot_frame_valid=True)
        task.snapshot['elements'][1]['frame']={'x':0,'y':0,'w':40,'h':20}
        with self.assertRaises(StopRun):task.click(args)

if __name__=='__main__':unittest.main()
