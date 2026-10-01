"""Report anti-fake-success checks; no real model or VM."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c1_report import validate_attempt, MODEL, phase_report, promotion_review, validate_session, measured_usage, TOKEN_FIELDS
from c1_cases import C1_CASES

class Report(unittest.TestCase):
    def row(self):
        expected=C1_CASES['popup'].expected
        return {'phase':'baseline','caseId':'popup','stage':'c1','hashes':{'a':'hash'},
            'manualInterventions':0,'elapsedMs':1000,'rawCalls':17,'status':'SUCCEEDED',
            'terminalReason':{'kind':'completed'},'verification':{'modelRoutes':[MODEL],'imageRequests':10,
            'independentGuestReport':{'status':'SUCCEEDED','case_id':'popup','expected':expected,
                'fresh_display':expected,'file_readback':expected,'raw_calls':17}}}
    def test_complete_matching_proof_is_required(self):
        row=self.row();validate_attempt(row,'baseline','popup',{'a':'hash'})
        for key,value in [('expected','fake'),('fresh_display','fake'),('file_readback','fake'),('status','UNVERIFIED'),('raw_calls',18)]:
            invalid=copy.deepcopy(row);invalid['verification']['independentGuestReport'][key]=value
            with self.assertRaises(ValueError):validate_attempt(invalid,'baseline','popup',{'a':'hash'})
    def test_no_budget_reset_or_model_source_drift(self):
        for key,value in [('rawCalls',31),('hashes',{'a':'different'}),('terminalReason',{'kind':'aborted'}),('elapsedMs',None),('manualInterventions',None)]:
            row=self.row();row[key]=value
            with self.assertRaises(ValueError):validate_attempt(row,'baseline','popup',{'a':'hash'})
        row=self.row();row['verification']['modelRoutes']=['another-model']
        with self.assertRaises(ValueError):validate_attempt(row,'baseline','popup',{'a':'hash'})
    def test_failure_is_retained_and_missing_phase_is_not_success(self):
        row=self.row();row.update(status='UNVERIFIED',verification={})
        validate_attempt(row,'baseline','popup',{'a':'hash'})
        with self.assertRaises(ValueError):phase_report([row],'baseline')
    def phases(self, candidate):
        phases={phase:{'perCase':{case:{'passed':3,'rawCalls':[21,18,19]} for case in C1_CASES}} for phase in ('baseline','after')}
        phases['after']['perCase']['popup']['rawCalls']=candidate
        return phases
    def test_gain_does_not_implicitly_prove_safety_or_enable_default(self):
        phases=self.phases([18,18,18])
        self.assertTrue(promotion_review(phases)['repeatableCostGain'])
        self.assertFalse(promotion_review(phases)['eligibleForDefault'])
        self.assertTrue(promotion_review(phases,safety_passed=True)['eligibleForDefault'])
    def test_declared_gain_threshold_and_success_regression_are_enforced(self):
        for values in ([19,19,19],[18,19,19],[18,18,30]):
            self.assertFalse(promotion_review(self.phases(values),safety_passed=True)['eligibleForDefault'])
        phases=self.phases([18,18,18]);phases['after']['perCase']['cross_app']['passed']=2
        self.assertFalse(promotion_review(phases,safety_passed=True)['eligibleForDefault'])
        phases=self.phases([17])
        with self.assertRaises(ValueError):promotion_review(phases,safety_passed=True)
    def test_report_cannot_replace_actual_terminal_session(self):
        row=self.row();row['modelToolCalls']=1
        events=[{'type':'turn/start'},{'type':'tool/call'},
            {'type':'turn/end','data':{'reason':{'kind':'completed'}}}]
        validate_session(events,row)
        for invalid in (events[:-1],events+events,events[:1]+events[2:]):
            with self.assertRaises(ValueError):validate_session(invalid,row)
        changed=copy.deepcopy(events);changed[-1]['data']['reason']={'kind':'aborted'}
        with self.assertRaises(ValueError):validate_session(changed,row)
    def test_usage_is_actual_or_unavailable_never_guessed(self):
        events=[{'type':'assistant/message','data':{'usage':{key:3 for key in TOKEN_FIELDS}}}]
        self.assertEqual(measured_usage(events)['totalTokens'],3)
        self.assertIsNone(measured_usage(events)['currencyCost'])
        events.append({'type':'assistant/message','data':{}})
        self.assertFalse(measured_usage(events)['available'])
        self.assertIsNone(measured_usage(events)['totalTokens'])

if __name__=='__main__':unittest.main()
