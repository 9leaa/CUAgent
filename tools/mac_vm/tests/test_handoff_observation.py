import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from handoff_observation import project_handoff_observation


class HandoffObservationTests(unittest.TestCase):
    def setUp(self):
        title = 'handoff-p2-11111111-1111-1111-1111-111111111111.txt'
        self.state = dict(snapshot_id='s', pid=10, window_id=20, app_name='TextEdit', window_title=title,
            screenshot_frame_valid=True, tree_markdown='irrelevant'*20000, elements=[
                dict(element_index=1, role='AXWindow', label=title),
                dict(element_index=2, parent_index=1, role='AXScrollArea'),
                dict(element_index=3, parent_index=2, role='AXTextArea', element_token='s:3', value='中文🙂\n完整正文'),
                dict(element_index=4, role='AXMenu', label='irrelevant'*10000)])

    def test_complete_body_original_identity_and_ancestors_preserved(self):
        before = copy.deepcopy(self.state)
        value = project_handoff_observation(self.state, 4)
        self.assertEqual(value['elements'], self.state['elements'][:2] + [dict(self.state['elements'][2], enabled=True)])
        self.assertNotIn('tree_markdown', value)
        self.assertLess(len(json.dumps(value, ensure_ascii=False).encode()), 1024)
        self.assertEqual(self.state, before)

    def test_ambiguity_dialog_cycles_disabled_and_invalid_identity_rejected(self):
        original = copy.deepcopy(self.state)
        for fault in ('duplicate', 'dialog', 'ambiguous', 'cycle', 'disabled', 'large', 'title', 'frame', 'token', 'index', 'parent'):
            self.state = copy.deepcopy(original); e = self.state['elements']
            if fault == 'duplicate': e.append(copy.deepcopy(e[0]))
            elif fault == 'dialog': e[3]['role'] = 'AXSheet'
            elif fault == 'ambiguous': e.append(dict(e[2], element_index=5))
            elif fault == 'cycle': e[1]['parent_index'] = 3
            elif fault == 'disabled': e[2]['enabled'] = False
            elif fault == 'large': e[2]['value'] = 'x'*4097
            elif fault == 'title': self.state['window_title'] = 'other'
            elif fault == 'frame': self.state['screenshot_frame_valid'] = False
            elif fault == 'token': e[2]['element_token'] = ''
            elif fault == 'index': e[0]['element_index'] = True
            else: e[1]['parent_index'] = True
            with self.subTest(fault=fault), self.assertRaises(ValueError): project_handoff_observation(self.state, 4)

    def test_missing_is_unknown_not_empty_and_invalid_values_rejected(self):
        body = self.state['elements'][2]
        del body['value']
        before = copy.deepcopy(self.state)
        projected = project_handoff_observation(self.state, 4)['elements'][-1]
        self.assertNotIn('value', projected)
        self.assertEqual(projected['bodyValueStatus'], 'unavailable')
        self.assertEqual(self.state, before)
        from real_app_bridge import body_from_state
        from c0_bridge import StopRun
        with self.assertRaises(StopRun):
            body_from_state(self.state)
        body['value'] = ''
        projected = project_handoff_observation(self.state, 4)['elements'][-1]
        self.assertEqual(projected['value'], '')
        self.assertNotIn('bodyValueStatus', projected)
        for invalid in (None, False, 0, [], {}):
            body['value'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                project_handoff_observation(self.state, 4)

    def test_no_truncation_to_fit_escaped_body_or_bad_budget(self):
        for used in (0, 31, True, 2.5):
            with self.assertRaises(ValueError): project_handoff_observation(self.state, used)
        self.state['elements'][2]['value'] = '\x01'*4096
        with self.assertRaises(ValueError): project_handoff_observation(self.state, 4)


if __name__ == '__main__': unittest.main()
