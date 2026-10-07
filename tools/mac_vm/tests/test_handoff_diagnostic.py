import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from handoff_diagnostic import TEXT, exercise


class DiagnosticTests(unittest.TestCase):
    def task(self):
        task = Mock(used=0, reopen_phase=None, uncertain=False, inflight=set())
        task.stopped.is_set.return_value = False
        task.observe.return_value = {'state': {'snapshot_id': 'fresh', 'elements': [
            {'role': 'AXTextArea', 'enabled': True, 'element_index': 3, 'element_token': 'fresh:3'}]}}
        task.observed_value.return_value = TEXT
        task.read_result.return_value = {'content': TEXT + '\n'}
        return task

    def test_sequence_is_not_business_acceptance(self):
        task = self.task(); renew = Mock()
        result = exercise(task, renew)
        self.assertTrue(result['sequenceCompleted'])
        self.assertEqual(result['businessStatus'], 'UNVERIFIED')
        self.assertEqual(result['modelCalls'], 0)
        self.assertEqual(renew.call_count, 10)
        task.reopen.assert_called_once()
        task.stop.assert_not_called()

    def test_unknown_reopen_stops_without_retry_or_result(self):
        task = self.task(); task.reopen.side_effect = RuntimeError('UNKNOWN')
        with self.assertRaises(RuntimeError): exercise(task, Mock())
        task.reopen.assert_called_once(); task.stop.assert_called_once()
        task.write_result.assert_not_called(); task.read_result.assert_not_called()

    def test_missing_enabled_matches_existing_executor(self):
        task = self.task()
        del task.observe.return_value['state']['elements'][0]['enabled']
        self.assertTrue(exercise(task, Mock())['sequenceCompleted'])
        task.type_text.assert_called_once()

    def test_explicit_disabled_or_invalid_enabled_is_refused(self):
        for enabled in (False, None, 1, 'true'):
            with self.subTest(enabled=enabled):
                task = self.task()
                task.observe.return_value['state']['elements'][0]['enabled'] = enabled
                with self.assertRaises(ValueError): exercise(task, Mock())
                task.type_text.assert_not_called()

    def test_old_task_refused_before_renewal(self):
        task = self.task(); task.used = 13; renew = Mock()
        with self.assertRaises(ValueError): exercise(task, renew)
        renew.assert_not_called(); task.observe.assert_not_called()

    def test_ambiguous_editor_refused(self):
        task = self.task(); task.observe.return_value['state']['elements'] *= 2
        with self.assertRaises(ValueError): exercise(task, Mock())
        task.type_text.assert_not_called(); task.stop.assert_called_once()

    def test_mismatched_readback_not_completed(self):
        task = self.task(); task.read_result.return_value = {'content': 'wrong'}
        with self.assertRaises(ValueError): exercise(task, Mock())
        task.stop.assert_called_once()

    def test_deadline_stops_before_next_renewal(self):
        task = self.task(); renew = Mock(); clock = Mock(side_effect=[0, 181])
        with self.assertRaises(ValueError): exercise(task, renew, clock=clock)
        renew.assert_not_called(); task.read_materials.assert_not_called()


if __name__ == '__main__':
    unittest.main()
