"""Focused policy tests; --live runs the fixed flow only inside the test VM."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from driver_smoke import BUTTONS, Calls, StopRun, button_in_window, display_value, main


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.calls_made = []
        self.calls = Calls(Path(self.tmp.name), transport=self.transport, identity=lambda pid: None)

    def transport(self, tool, args):
        self.calls_made.append((tool, args))
        return {}

    def tearDown(self):
        self.calls.log.close()
        self.tmp.cleanup()

    def test_other_app_and_shell_rejected_before_dispatch(self):
        for tool, args in [('launch_app', {'bundle_id': 'com.apple.Terminal'}),
                           ('shell', {'command': 'true'})]:
            with self.assertRaises(StopRun) as caught:
                self.calls.invoke(tool, args)
            self.assertEqual(caught.exception.status, 'BLOCKED')
        self.assertEqual(self.calls_made, [])

    def test_budget_includes_observations(self):
        for _ in range(30):
            self.calls.invoke('launch_app', {'bundle_id': 'com.apple.calculator'})
        with self.assertRaises(StopRun):
            self.calls.invoke('launch_app', {'bundle_id': 'com.apple.calculator'})
        self.assertEqual(len(self.calls_made), 30)

    def test_action_timeout_is_unknown_and_not_replayed(self):
        def timeout(tool, args):
            self.calls_made.append(tool)
            raise subprocess.TimeoutExpired(tool, 35)
        self.calls.transport = timeout
        with self.assertRaises(StopRun) as caught:
            self.calls.invoke('launch_app', {'bundle_id': 'com.apple.calculator'})
        self.assertEqual(caught.exception.status, 'UNVERIFIED')
        rows = [json.loads(x) for x in (Path(self.tmp.name)/'trace.jsonl').read_text().splitlines()]
        self.assertEqual([x['status'] for x in rows], ['DISPATCHED', 'UNKNOWN'])
        self.assertEqual(len(self.calls_made), 1)

    def test_process_identity_failure_prevents_observation(self):
        def reject(pid):
            raise StopRun('BLOCKED', 'not Calculator')
        self.calls.pid = 99
        self.calls.identity = reject
        with self.assertRaises(StopRun):
            self.calls.invoke('list_windows', {'pid': 99})
        self.assertEqual(self.calls_made, [])

    def test_positive_snapshot_does_not_require_full_tree_claim(self):
        self.calls.pid, self.calls.window_id = 99, 50
        self.calls.transport = lambda *_: dict(pid=99, window_id=50, app_name='Calculator',
            window_title='Calculator', snapshot_id='s1', elements_complete=False,
            screenshot_frame_valid=True)
        self.assertEqual(self.calls.observe()['snapshot_id'], 's1')

    def test_menu_button_not_allowed(self):
        state = {'elements': [{'element_index': 0, 'role': 'AXMenu', 'label': 'Calculator'},
                             {'role': 'AXButton', 'label': '1', 'parent_index': 0,
                              'enabled': True, 'actions': ['AXPress']}]}
        with self.assertRaises(StopRun):
            button_in_window(state, '1')

    def test_missing_ambiguous_or_menu_result_is_unverified(self):
        for text in ['', '- AXWindow\n- AXMenu\n  - AXStaticText = "408"',
                     '- AXWindow\n  - AXStaticText = "12"\n  - AXStaticText = "34"']:
            with self.assertRaises(StopRun):
                display_value({'tree_markdown': text})
        self.assertEqual(display_value({'tree_markdown': '- AXWindow\n  - AXStaticText = "\u200e408"'}), '408')


def live():
    directory, report = main()
    rows = [json.loads(x) for x in (directory/'trace.jsonl').read_text().splitlines()]
    completed = [r for r in rows if r['status'] != 'DISPATCHED']
    actions = [r for r in completed if r['tool'] == 'click']
    passed = False
    if report['execution_complete']:
        final = json.loads((directory/'final_state.json').read_text())
        screenshot = Path(report['final_screenshot'])
        passed = (report['observed_display'] == str(12 * 34) == display_value(final)
                  and tuple(r['button_label'] for r in actions) == BUTTONS
                  and all(r['status'] == 'RETURNED' for r in completed)
                  and len(completed) == report['tool_calls'] <= 30
                  and screenshot.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
    validation = {'phase': 'M1', 'passed': passed, 'run_id': directory.name,
                  'tool_calls': report['tool_calls'], 'expected': 12 * 34,
                  'observed': report.get('observed_display'),
                  'scope': 'fixed flow plus independent smoke assertion; not M3 result-file verification'}
    (directory/'smoke_assertion.json').write_text(json.dumps(validation, indent=2))
    print(json.dumps(validation, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--live']:
        sys.exit(live())
    unittest.main()
