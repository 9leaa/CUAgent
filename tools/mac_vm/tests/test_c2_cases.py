"""C2 gate-definition checks only, not live fault or release evidence."""
import dataclasses
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from c2_cases import C2_CASES, FAULTS, schedule, RAW_BUDGET, MIN_SUCCESSES, CALCULATOR_REGRESSIONS, SAFETY_GATES, A0_GATES
from c1_cases import C1_CASES

class C2Registry(unittest.TestCase):
    def test_original_six_categories_are_not_reduced_or_reused_as_results(self):
        self.assertEqual(dict(C2_CASES),dict(C1_CASES))
        self.assertEqual(len(schedule()),18)
        self.assertEqual(len(set(schedule())),18)
        for case in C1_CASES:self.assertEqual([n for c,n in schedule() if c==case],[1,2,3])
        self.assertEqual((RAW_BUDGET,MIN_SUCCESSES),(30,17))
        self.assertEqual(len(CALCULATOR_REGRESSIONS),9)
    def test_all_seven_faults_and_real_permission_gate_are_fixed(self):
        self.assertEqual(set(FAULTS),{'effect_then_timeout','process_exit','window_closed',
            'manual_document_edit','model_failure','permission_revoked','budget_exhausted'})
        self.assertIn('actual_guest_permission_revocation',FAULTS['permission_revoked'].evidence)
        self.assertIn('actual_gui_document_change',FAULTS['manual_document_edit'].evidence)
        self.assertIn('no_duplicate_effect',FAULTS['effect_then_timeout'].evidence)
        self.assertFalse(FAULTS['budget_exhausted'].business_success_required)
        self.assertIn('not_business_success',FAULTS['budget_exhausted'].evidence)
    def test_safety_and_a0_are_required_and_definitions_are_immutable(self):
        self.assertIn('stop_inflight',SAFETY_GATES)
        self.assertIn('false_success',SAFETY_GATES)
        self.assertIn('unknown_reconciliation',SAFETY_GATES)
        self.assertIn('session_model_restart',A0_GATES)
        self.assertIn('direct_image',A0_GATES)
        self.assertIn('tool_image',A0_GATES)
        with self.assertRaises(TypeError):FAULTS['new']=FAULTS['process_exit']
        with self.assertRaises(dataclasses.FrozenInstanceError):FAULTS['process_exit'].business_success_required=False

if __name__=='__main__':unittest.main()
