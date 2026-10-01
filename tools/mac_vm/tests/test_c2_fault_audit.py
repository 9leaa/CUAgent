"""Synthetic negative proofs only; these do not inject a real VM fault."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c2_fault_audit import audit_timeout


class TimeoutAudit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        intent={'label':'Submit','snapshot_id':'before','pid':123,'window_id':456}
        self.rows=[
            {'event':'c2_control','epoch':1,'owner':'model','reason':'initial_session','policy':'c2-ownership-v1'},
            {'event':'dispatch','used':1,'call_id':'lost','tool':'click','intent':intent},
            {'event':'c2_fault_injected','fault':'submit_response_timeout','layer':'after_actual_driver_response','intent':copy.deepcopy(intent)},
            {'event':'UNKNOWN','tool':'click','call_id':'lost'},
            {'event':'stop'},
            {'event':'c2_control','epoch':2,'owner':'paused','reason':'stop','policy':'c2-ownership-v1'},
            {'event':'dispatch','used':2,'call_id':'fresh','tool':'get_window_state','recovery_observation':True,'control_epoch':2},
            {'event':'result','tool':'get_window_state','call_id':'fresh','value':{
                'snapshot_id':'after','pid':123,'window_id':456,'screenshot_frame_valid':True,
                'tree_markdown':'AXWindow\n  - AXStaticText = "Submitted cedar-42"'}},
            {'event':'c2_reconciled_call','call_id':'lost','verdict':'applied','snapshot_id':'after','pid':123,'window_id':456},
            {'event':'completed_action','label':'Submit'},
            {'event':'c2_control','epoch':3,'owner':'human','reason':'takeover','policy':'c2-ownership-v1'},
            {'event':'c2_control','epoch':4,'owner':'model','reason':'explicit_resume','policy':'c2-ownership-v1'},
        ]
        self.verification={'case_id':'input_correction','status':'SUCCEEDED','raw_calls':2,
            'fresh_display':'Submitted cedar-42','file_readback':'Submitted cedar-42',
            'expected':'Submitted cedar-42','reconciled_calls':['lost']}
        self.effects=['submit']
        self.result='Submitted cedar-42'

    def audit(self):
        # Test fixtures are generated in a disposable directory, not runtime evidence.
        (self.directory/'trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.rows))
        (self.directory/'verification.json').write_text(json.dumps(self.verification))
        (self.directory/'c1-effects.json').write_text(json.dumps({'effects':self.effects}))
        (self.directory/'result.txt').write_text(self.result)
        return audit_timeout(self.directory)

    def test_minimal_consistent_synthetic_proof(self):
        self.assertEqual(self.audit()['gateStatus'],'PASS')
        self.assertIn('not C2 release',self.audit()['scope'])

    def test_missing_unknown_or_fresh_observation_is_rejected(self):
        original=copy.deepcopy(self.rows)
        for event in ('UNKNOWN','result'):
            with self.subTest(event=event):
                self.rows=[r for r in copy.deepcopy(original) if r['event']!=event]
                with self.assertRaises(ValueError):self.audit()

    def test_duplicate_effect_or_completed_action_is_rejected(self):
        self.effects.append('submit')
        with self.assertRaises(ValueError):self.audit()
        self.effects=['submit']
        self.rows.append({'event':'completed_action','label':'Submit'})
        with self.assertRaises(ValueError):self.audit()

    def test_fake_or_other_window_observation_is_rejected(self):
        state=copy.deepcopy(self.rows[7]['value'])
        for key,value in (('pid',999),('window_id',999),('screenshot_frame_valid',False),
                          ('tree_markdown','AXWindow\n  - AXStaticText = "Submitted fake"')):
            with self.subTest(key=key):
                self.rows[7]['value']={**state,key:value}
                with self.assertRaises(ValueError):self.audit()

    def test_old_snapshot_or_premature_receipt_is_rejected(self):
        self.rows[8]['snapshot_id']='before'
        with self.assertRaises(ValueError):self.audit()
        self.rows[8]['snapshot_id']='after'
        self.rows[7],self.rows[8]=self.rows[8],self.rows[7]
        with self.assertRaises(ValueError):self.audit()

    def test_fake_budget_or_result_readback_is_rejected(self):
        self.verification['raw_calls']=1
        with self.assertRaises(ValueError):self.audit()
        self.verification['raw_calls']=2
        self.result='Submitted fake'
        with self.assertRaises(ValueError):self.audit()
        self.result='Submitted cedar-42'
        self.verification['file_readback']='Submitted fake'
        with self.assertRaises(ValueError):self.audit()

    def test_wrong_injection_or_normal_success_for_unknown_is_rejected(self):
        self.rows[2]['intent']['pid']=999
        with self.assertRaises(ValueError):self.audit()
        self.rows[2]['intent']['pid']=123
        self.rows.append({'event':'result','call_id':'lost'})
        with self.assertRaises(ValueError):self.audit()

    def test_paused_input_or_bad_control_epoch_is_rejected(self):
        self.rows[6]['tool']='click'
        with self.assertRaises(ValueError):self.audit()
        self.rows[6]['tool']='get_window_state'
        self.rows[11]['epoch']=True
        with self.assertRaises(ValueError):self.audit()

    def test_evidence_link_is_rejected(self):
        self.audit()
        target=self.directory/'result.txt'
        target.rename(self.directory/'original.txt')
        target.symlink_to(self.directory/'original.txt')
        with self.assertRaises(ValueError):audit_timeout(self.directory)


if __name__=='__main__':unittest.main()
