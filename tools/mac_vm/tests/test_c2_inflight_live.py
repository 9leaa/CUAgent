"""In-flight diagnostic mocks/antifake checks, not real GUI evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from c2_bridge import C2Task
from c2_inflight_live import exercise, audit


class InflightDiagnostic(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name) / 'c2-inflight-mock'
        self.value = 'cedra-42'
        self.calls = []
        self.task = C2Task(self.directory, self.transport, lambda _: None,
                           approved=True, case_id='input_correction')

    def tearDown(self):
        self.temp.cleanup()

    def transport(self, tool, args):
        self.calls.append(tool)
        if tool == 'launch_app':
            return {'bundle_id': 'org.cuagent.fixtures', 'pid': 11}
        if tool == 'list_windows':
            return {'windows': [{'pid': 11, 'window_id': 12, 'title': 'CUAgent Correction',
                                'app_name': 'CUAgentFixtures', 'is_on_screen': True}]}
        if tool == 'type_text':
            self.value = args['text']
            return {'effect': 'unverifiable'}
        self.assertEqual(tool, 'get_window_state')
        Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\n')
        return {'pid': 11, 'window_id': 12, 'app_name': 'CUAgentFixtures',
                'window_title': 'CUAgent Correction', 'snapshot_id': 'mock-' + str(len(self.calls)),
                'screenshot_frame_valid': True, 'tree_markdown': '- AXWindow',
                'elements': [{'role': 'AXWindow', 'label': 'CUAgent Correction', 'element_index': 0},
                             {'role': 'AXTextField', 'label': 'Code', 'element_index': 1,
                              'element_token': 'field-' + str(len(self.calls)), 'parent_index': 0,
                              'enabled': True, 'value': self.value}]}

    def mutate(self, modify):
        path = self.directory / 'trace.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        modify(rows)
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def test_stop_tracks_actual_inflight_and_refuses_premature_handoff(self):
        elapsed = exercise(self.task)
        self.assertLess(elapsed, 1)
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(audit(self.directory)['taskStatus'], 'UNVERIFIED')

    def test_stop_without_inflight_identity_is_not_proof(self):
        exercise(self.task)
        def strip(rows):
            next(row for row in rows if row['event'] == 'stop')['inflight'] = []
        self.mutate(strip)
        with self.assertRaises(AssertionError):
            audit(self.directory)

    def test_recovery_without_actual_changed_field_is_not_proof(self):
        exercise(self.task)
        def unchanged(rows):
            states = [row['value'] for row in rows if row['event'] == 'result' and row['tool'] == 'get_window_state']
            states[-1]['elements'][-1]['value'] = 'cedra-42'
        self.mutate(unchanged)
        with self.assertRaises(AssertionError):
            audit(self.directory)


if __name__ == '__main__':
    unittest.main()
