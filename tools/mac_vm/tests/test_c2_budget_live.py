"""Budget diagnostic antifake mocks; never counts as real Driver evidence."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import c2_budget_live as budget
from c2_bridge import C2Task


class BudgetDiagnostic(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.directory = self.home / 'C0Evidence' / 'c2_budget_mock'
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def transport(self, tool, args):
        self.calls.append(tool)
        if tool == 'launch_app':
            return {'bundle_id': 'org.cuagent.fixtures', 'pid': 11}
        if tool == 'list_windows':
            return {'windows': [{'pid': 11, 'window_id': 12, 'title': 'CUAgent Correction',
                                'app_name': 'CUAgentFixtures', 'is_on_screen': True}]}
        self.assertEqual(tool, 'get_window_state')
        Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\n')
        return {'pid': 11, 'window_id': 12, 'app_name': 'CUAgentFixtures',
                'window_title': 'CUAgent Correction', 'snapshot_id': 'mock-' + str(len(self.calls)),
                'screenshot_frame_valid': True, 'tree_markdown': '- AXWindow'}

    def execute(self, stage, pid):
        def factory(directory, **kwargs):
            return C2Task(directory, self.transport, lambda _: None, **kwargs)
        with patch.object(budget, 'require_vm'), patch.object(budget.Path, 'home', return_value=self.home), \
             patch.object(budget, 'C2Task', side_effect=factory), patch.object(budget.os, 'getpid', return_value=pid), \
             contextlib.redirect_stdout(io.StringIO()):
            budget.run('c2_budget_mock', stage, True)

    def prepare(self):
        self.execute('fill', 100)
        self.assertEqual(len(self.calls), 30)
        self.execute('restart', 101)
        self.assertEqual(len(self.calls), 30)

    def rewrite_rows(self, modify):
        path = self.directory / 'trace.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        modify(rows)
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def test_actual_counter_fill_and_separate_process_refusal(self):
        self.prepare()
        report = budget.audit(self.directory)
        self.assertEqual(report['taskStatus'], 'UNVERIFIED')
        self.assertEqual(report['actualObservations'], 28)
        self.assertEqual(report['rawCalls'], 30)
        with self.assertRaises(ValueError):
            self.execute('fill', 102)

    def test_missing_actual_result_cannot_pass(self):
        self.prepare()
        def remove(rows):
            rows.remove(next(row for row in rows if row['event'] == 'result'))
        self.rewrite_rows(remove)
        with self.assertRaises(AssertionError):
            budget.audit(self.directory)

    def test_duplicate_observation_cannot_pass(self):
        self.prepare()
        def duplicate(rows):
            states = [row['value'] for row in rows if row.get('tool') == 'get_window_state' and row['event'] == 'result']
            states[-1]['snapshot_id'] = states[0]['snapshot_id']
        self.rewrite_rows(duplicate)
        with self.assertRaises(AssertionError):
            budget.audit(self.directory)

    def test_same_process_is_not_restart_evidence(self):
        self.prepare()
        path = self.directory / 'budget-restart.json'
        report = json.loads(path.read_text())
        report['executor_pid'] = 100
        path.write_text(json.dumps(report))
        with self.assertRaises(AssertionError):
            budget.audit(self.directory)

    def test_business_success_artifact_cannot_be_misreported(self):
        self.prepare()
        (self.directory / 'verification.json').write_text('{"status":"SUCCEEDED"}')
        with self.assertRaises(AssertionError):
            budget.audit(self.directory)


if __name__ == '__main__':
    unittest.main()
