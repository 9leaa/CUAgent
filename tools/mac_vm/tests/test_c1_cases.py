"""Registry checks only: not C1 VM or model success evidence."""
import dataclasses
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from c1_cases import C1_CASES, PHASES, RAW_BUDGET, schedule

class C1Registry(unittest.TestCase):
    def test_all_original_categories_have_three_before_and_after_attempts(self):
        categories={'cross_app','popup','window_change','input_correction','long_workflow','reobserve_failure'}
        self.assertEqual(set(C1_CASES),categories)
        self.assertEqual(len(schedule()),36)
        self.assertEqual(len(set(schedule())),36)
        for phase in PHASES:
            for case_id in categories:
                self.assertEqual([n for p,c,n in schedule() if p==phase and c==case_id],[1,2,3])
        self.assertEqual(RAW_BUDGET,30)

    def test_registry_is_immutable_and_cross_app_is_not_one_fixture(self):
        with self.assertRaises(TypeError):C1_CASES['other']=C1_CASES['popup']
        with self.assertRaises(dataclasses.FrozenInstanceError):C1_CASES['popup'].expected='fake'
        calc,receiver=C1_CASES['cross_app'].applications
        self.assertNotEqual(calc.bundle,receiver.bundle)
        self.assertNotEqual(calc.executable,receiver.executable)
        self.assertNotIn('15',C1_CASES['cross_app'].prompt)

    def test_proofs_are_explicit_and_recovery_needs_a_new_observation(self):
        for case in C1_CASES.values():
            self.assertTrue(case.expected)
            self.assertTrue(case.required_effects)
            self.assertTrue(case.applications)
            self.assertTrue(case.prompt)
        self.assertIn('fresh-observation-after-refusal',C1_CASES['reobserve_failure'].required_effects)
        self.assertIn('different-window-id',C1_CASES['window_change'].required_effects)
        self.assertEqual(len([x for x in C1_CASES['long_workflow'].required_effects if x.startswith('stage:')]),3)

if __name__=='__main__':unittest.main()
