"""No model or VM: explicit real-app policy and false-success tests."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from real_app_bridge import RealAppTask, body_from_state, require_unlocked
import plistlib
from driver_smoke import StopRun


class RealApp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.sent = []
        self.task = RealAppTask(Path(self.temp.name) / 'new_run',
                                lambda tool, args: self.sent.append((tool, args)) or {'ok': True},
                                lambda _: None, approved=True, environment=lambda: None)
    def tearDown(self):
        self.temp.cleanup()
    def snapshot(self, value=''):
        task = self.task
        task.pid, task.window = 10, 20
        task.snapshot = {'snapshot_id': 'fresh', 'window_title': task.case.title, 'tree_markdown': '- AXWindow ' + task.case.title + '\n  - AXTextArea = ' + json.dumps(value),
                         'elements': [{'element_index': 0, 'role': 'AXWindow', 'label': task.case.title},
                                      {'element_index': 1, 'parent_index': 0, 'element_token': 'token',
                                       'role': 'AXTextArea', 'enabled': True}]}
        task.observed_at = time.monotonic()
        return {'snapshot_id': 'fresh', 'element_index': 1, 'element_token': 'token'}
    def test_non_hardcoded_body_and_fresh_single_action(self):
        args = self.snapshot()
        self.task.type_text({**args, 'text': 'A genuinely new note.'})
        self.assertEqual(self.sent[0][0], 'type_text')
        with self.assertRaises(StopRun):
            self.task.type_text({**args, 'text': 'second write without observing'})
    def test_text_type_size_nul_extra_fields(self):
        for text in ('', '\0', 'x' * 4097, 123):
            with self.assertRaises(StopRun): self.task.type_text({**self.snapshot(), 'text': text})
        with self.assertRaises(StopRun): self.task.type_text({**self.snapshot(), 'text': 'ok', 'path': '/private'})
        self.assertEqual(self.task.used, 0)
    def test_other_window_stale_and_wrong_role(self):
        args = self.snapshot()
        self.task.snapshot['elements'][0]['label'] = 'other.txt'
        with self.assertRaises(StopRun): self.task.type_text({**args, 'text': 'no'})
        args = self.snapshot(); self.task.observed_at -= 31
        with self.assertRaises(StopRun): self.task.type_text({**args, 'text': 'no'})
        args = self.snapshot(); self.task.snapshot['elements'][1]['role'] = 'AXTextField'
        with self.assertRaises(StopRun): self.task.type_text({**args, 'text': 'no'})
    def test_save_only_exact_shortcut(self):
        self.snapshot('note'); self.task.save({'snapshot_id': 'fresh'})
        self.assertEqual(self.sent[0][0], 'hotkey')
        self.assertEqual(self.sent[0][1]['keys'], ['cmd', 's'])
        with self.assertRaises(StopRun): self.task.save({'snapshot_id': 'fresh'})
        for key, modifiers in [('s', ['cmd', 'shift']), ('q', ['cmd']), ('return', [])]:
            with self.assertRaises(StopRun): self.task.raw('press_key', {'pid': 10, 'window_id': 20,
                'session': self.task.run_id, 'key': key, 'modifiers': modifiers, 'delivery_mode': 'foreground'})
        for keys in (['cmd', 'shift', 's'], ['cmd', 'q'], ['cmd', 'o']):
            with self.assertRaises(StopRun): self.task.raw('hotkey', {'pid': 10, 'window_id': 20,
                'session': self.task.run_id, 'keys': keys, 'delivery_mode': 'foreground'})
        with self.assertRaises(StopRun): self.task.click({})
    def test_unsaved_body_and_artifact_link_denied(self):
        self.snapshot('not saved')
        with self.assertRaises(StopRun): self.task.observed_value()
        self.task.document.unlink(); self.task.document.symlink_to(Path(self.temp.name) / 'outside')
        with self.assertRaises(StopRun): self.task.observed_value()
    def test_display_projection_only_allows_one_terminal_lf(self):
        self.snapshot('visible body')
        self.task.document.write_text('visible body\n')
        self.assertEqual(self.task.observed_value(), 'visible body\n')
        for content in ('visible body\n\n', 'visible body ', 'visible body\ns', 'wrong body\n'):
            self.task.document.write_text(content)
            with self.assertRaises(StopRun): self.task.observed_value()
    def test_capture_mismatch_reobserves_once_without_input_or_rescale(self):
        self.task.pid, self.task.window = 10, 20
        state = {'pid': 10, 'window_id': 20, 'window_title': self.task.case.title, 'app_name': 'TextEdit',
                 'screenshot_error': {'code': 'px_frame_mismatch'}}
        counter = [0]
        def invalid_capture(*_):
            counter[0] += 1
            self.task.record({'event': 'result', 'tool': 'get_window_state', 'value': state})
            raise StopRun('UNVERIFIED', 'invalid capture')
        with patch('real_app_bridge.Task.observe', side_effect=invalid_capture):
            with self.assertRaises(StopRun): self.task.observe()
        self.assertEqual(counter[0], 2)
        self.assertTrue(self.task.stopped.is_set())
        self.assertEqual(self.sent, [])
    def test_budget_stop_and_restart_preserved(self):
        for _ in range(30): self.task.raw('launch_app', self.task.launch_args)
        with self.assertRaises(StopRun): self.task.raw('launch_app', self.task.launch_args)
        restarted = RealAppTask(self.task.directory, approved=True, identity=lambda _: None, environment=lambda: None)
        self.assertEqual(restarted.used, 30)
        self.assertTrue(restarted.stopped.is_set())
        with self.assertRaises(StopRun): restarted.admit('get_window_state')
        self.assertEqual(len(self.sent), 30)
    def test_native_body_requires_unique_value_not_menu(self):
        self.assertEqual(body_from_state({'tree_markdown': '- AXWindow\n  - AXTextArea = "line1\\nline2"\n- AXMenuBar'}), 'line1\nline2')
        for tree in ('- AXWindow\n- AXMenuBar\n  - AXTextArea = "menu"', '- AXWindow\n  - AXStaticText = "fake"',
                     '- AXWindow\n  - AXTextArea = "a"\n  - AXTextArea = "b"'):
            with self.assertRaises(StopRun): body_from_state({'tree_markdown': tree})
    def test_file_alone_is_not_success(self):
        text = 'new result'
        self.task.document.write_text(text)
        (self.task.directory / 'verifier-expected.txt').write_text(text)
        (self.task.directory / 'result.txt').write_text(text + '\n')
        self.snapshot(text)
        with patch.object(self.task, 'observe'):
            self.assertEqual(self.task.verify()['status'], 'UNVERIFIED')
    def test_structured_native_value_and_ambiguous_refusal(self):
        self.snapshot('fallback')
        self.task.snapshot['elements'][1]['value'] = 'native body\n'
        self.assertEqual(body_from_state(self.task.snapshot), 'native body\n')
        self.task.snapshot['elements'].append({**self.task.snapshot['elements'][1], 'element_index': 2})
        with self.assertRaises(StopRun): body_from_state(self.task.snapshot)
    def test_no_arbitrary_activation(self):
        self.snapshot()
        with self.assertRaises(StopRun): self.task.raw('bring_to_front', {'pid': 10, 'window_id': 20})
    def test_lock_state_refused_before_dispatch(self):
        def locked(): raise StopRun('BLOCKED', 'VM locked')
        self.task.environment = locked
        with self.assertRaises(StopRun): self.task.raw('launch_app', self.task.launch_args)
        self.assertEqual(self.task.used, 0)
        self.assertEqual(self.sent, [])
    def test_console_owner_is_not_proof_of_unlocked_state(self):
        base = {'kCGSSessionUserNameKey': 'mvpagent', 'kCGSSessionOnConsoleKey': True, 'kCGSessionLoginDoneKey': True}
        for user, valid in [(base, True), ({**base, 'CGSSessionScreenIsLocked': True}, False),
                            ({**base, 'kCGSSessionOnConsoleKey': False}, False)]:
            with patch('real_app_bridge.require_vm'), patch('real_app_bridge.subprocess.check_output', return_value=plistlib.dumps({'IOConsoleUsers': [user]})):
                if valid: require_unlocked()
                else:
                    with self.assertRaises(StopRun): require_unlocked()
        self.assertEqual(self.task.used, 0)
    def test_one_bound_activation_only_after_real_degraded_observation(self):
        self.task.pid, self.task.window = 10, 20
        degraded = {'pid': 10, 'window_id': 20, 'window_title': self.task.case.title, 'app_name': 'TextEdit',
                    'screenshot_frame_valid': True, 'degraded_reason': 'ax_window_unresolved: test'}
        def failed_observe(*_):
            self.task.record({'event': 'result', 'tool': 'get_window_state', 'value': degraded})
            raise StopRun('UNVERIFIED', 'missing native body')
        with patch('real_app_bridge.Task.observe', side_effect=failed_observe):
            with self.assertRaises(StopRun): self.task.observe()
        self.assertEqual([tool for tool, _ in self.sent], ['bring_to_front'])
        self.assertTrue(self.task.stopped.is_set())
        with self.assertRaises(StopRun): self.task.raw('bring_to_front', {'pid': 10, 'window_id': 20})
