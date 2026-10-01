"""Synthetic audit negatives, not real GUI/fault evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c2_window_audit import audit_window


class WindowAudit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name);self.rows=[];self.used=0
        def control(epoch,owner,reason):self.rows.append({'event':'c2_control','epoch':epoch,'owner':owner,'reason':reason,'policy':'c2-ownership-v1'})
        def request(tool,value,**extra):
            self.used+=1
            self.rows.extend([{'event':'dispatch','tool':tool,'used':self.used,'call_id':str(self.used),**extra},
                              {'event':'result','tool':tool,'call_id':str(self.used),'value':value}])
        control(1,'model','initial_session');self.rows.append({'event':'stop'})
        control(2,'paused','stop');control(3,'human','takeover')
        request('get_window_state',{'snapshot_id':'old','pid':11,'window_id':12,'screenshot_frame_valid':True,
            'window_bounds':{'x':320,'y':25},'elements':[
                {'role':'AXWindow','element_index':0,'label':'CUAgent Correction'},
                {'role':'AXButton','element_index':3,'element_token':'close','enabled':True,'parent_index':0,
                 'actions':['AXPress'],'frame':{'x':326,'y':31,'w':16,'h':16}},
            ]},recovery_observation=True,control_epoch=3)
        self.rows.append({'event':'c2_window_close_attempt','pid':11,'window_id':12,'snapshot_id':'old','element_index':3,'element_token':'close'})
        request('click',{},developer_control=True,control_epoch=3)
        request('list_windows',{'windows':[]},developer_control=True,control_epoch=3)
        self.rows.extend([{'event':'c2_window_closed','pid':11,'window_id':12},
                          {'event':'c2_fault_injected','fault':'window_close_after_observe','layer':'actual_driver_close_and_fresh_inventory'}])
        request('reopen_task_application',{'not_window_proof':True},developer_control=True,control_epoch=3)
        self.rows.append({'event':'c2_window_reopen_requested','pid':11,'old_window_id':12})
        request('get_window_state',{'pid':11,'window_id':13,'screenshot_frame_valid':True},recovery_observation=True,control_epoch=3)
        control(4,'model','explicit_resume')
        request('rejected_click',{'reason':'Fresh observation required'})
        self.effects=['initial-value:cedra-42','corrected-value:cedar-42','submit']
        self.verification={'status':'SUCCEEDED','case_id':'input_correction','raw_calls':6,'actions':['Submit'],
            'fresh_display':'Submitted cedar-42','file_readback':'Submitted cedar-42','expected':'Submitted cedar-42'}

    def audit(self):
        (self.directory/'trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.rows))
        (self.directory/'verification.json').write_text(json.dumps(self.verification))
        (self.directory/'c1-effects.json').write_text(json.dumps({'effects':self.effects}))
        (self.directory/'result.txt').write_text('Submitted cedar-42')
        return audit_window(self.directory)

    def test_consistent_synthetic_proof_is_not_full_release(self):
        result=self.audit();self.assertEqual(result['gateStatus'],'PASS')
        self.assertIn('not complete C2 release',result['scope'])

    def test_old_window_or_other_process_is_rejected(self):
        state=next(r for r in self.rows if r['event']=='result' and r.get('tool')=='get_window_state' and 'snapshot_id' not in r['value'])
        original=copy.deepcopy(state['value'])
        for key,value in (('pid',99),('window_id',12),('screenshot_frame_valid',False)):
            with self.subTest(key=key):
                state['value']={**original,key:value}
                with self.assertRaises(ValueError):self.audit()

    def test_close_missing_or_unrelated_close_button_is_rejected(self):
        state=next(r for r in self.rows if r['event']=='result' and r.get('value',{}).get('snapshot_id')=='old')
        state['value']['elements'][1]['frame']['x']=500
        with self.assertRaises(ValueError):self.audit()

    def test_duplicated_effect_or_reset_budget_is_rejected(self):
        self.effects.append('submit')
        with self.assertRaises(ValueError):self.audit()
        self.effects.pop()
        self.verification['raw_calls']=1
        with self.assertRaises(ValueError):self.audit()

    def test_missing_old_refusal_or_unknown_is_rejected(self):
        original=copy.deepcopy(self.rows)
        self.rows=[r for r in self.rows if r.get('tool')!='rejected_click']
        self.verification['raw_calls']=5
        with self.assertRaises(ValueError):self.audit()
        self.rows=original;self.verification['raw_calls']=6
        self.rows.append({'event':'UNKNOWN','call_id':'2'})
        with self.assertRaises(ValueError):self.audit()


if __name__=='__main__':unittest.main()
