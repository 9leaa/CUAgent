import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_handoff_trace
from handoff_exchanges import match_handoff_exchanges


class HandoffExchangeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_handoff_trace.HandoffTraceTests(); self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        f = self.fixture
        source = json.loads(f.materials)
        hashes = {**{'notes/' + n['id']: hashlib.sha256(n['content'].encode()).hexdigest() for n in source['notes']},
                  **{k: hashlib.sha256(source[k].encode()).hexdigest() for k in ('tasksCsv', 'previousReport')}}
        states = [r['value'] for r in f.rows if r['event'] == 'result' and r.get('tool') == 'get_window_state']
        def projected(state, used):
            return dict(projection='handoff-body-v1', **{k: state[k] for k in (
                'snapshot_id', 'pid', 'window_id', 'app_name', 'window_title', 'screenshot_frame_valid')}, used=used,
                elements=[state['elements'][0], dict(state['elements'][1], enabled=True)])
        self.rows = []
        def call(name, args, value, image=False):
            key = str(len(self.rows)); seq = len(self.rows)
            content = [dict(type='text', text=json.dumps(value, ensure_ascii=False))]
            if image: content.append(dict(type='image', attachment=dict(attachmentId='sha256:' + 'a' * 64,
                mediaType='image/webp', bytes=1234, width=800, height=600, name='vm-calculator.png')))
            self.rows.extend([dict(type='tool/call', seq=seq, data=dict(callId=key, name=name, arguments=json.dumps(args))),
                dict(type='tool/result', seq=seq+1, data=dict(message=dict(toolCallId=key, isError=False, content=content)))])
        call('vm_read_materials', {}, dict(materials=source, sourceHashes=hashes,
             inputSha256=hashlib.sha256(f.materials).hexdigest(), used=1))
        call('vm_observe', {}, projected(states[0], 4), True)
        call('vm_type', dict(snapshot_id='1', element_index=2, element_token='body', text=f.expected.decode()), dict(ok=True))
        call('vm_observe', {}, projected(states[1], 6), True)
        call('vm_save', dict(snapshot_id='2'), dict(ok=True))
        call('vm_observe', {}, projected(states[2], 8), True)
        call('vm_reopen', dict(snapshot_id='3'), dict(requires_new_observation=True, used=12))
        call('vm_observe', {}, projected(states[3], 13), True)
        call('vm_write_result', dict(snapshot_id='4', value=f.expected.decode()),
             dict(created='result.txt', value=f.expected.decode(), used=14))
        call('vm_read_result', {}, dict(content=f.expected.decode()+'\n', used=15))

    def match(self):
        f = self.fixture
        return match_handoff_exchanges(self.rows, f.rows, run_id=f.run, materials=f.materials, expected=f.expected)

    def test_all_ten_logical_calls_match_fifteen_raw_without_image_claim(self):
        original = copy.deepcopy(self.rows)
        result = self.match()
        self.assertEqual(result['status'], 'EXCHANGES_MATCHED')
        self.assertEqual((result['officialToolCalls'], result['rawCalls']), (10, 15))
        self.assertEqual(len(result['attachmentsToVerify']), 4)
        self.assertFalse(result['sessionVerified']); self.assertFalse(result['imageBytesVerified'])
        self.assertEqual(self.rows, original)

    def test_every_request_and_response_is_bound_not_just_counted(self):
        original = copy.deepcopy(self.rows)
        for i in range(0, len(original), 2):
            self.rows = copy.deepcopy(original)
            self.rows[i]['data']['arguments'] = '{"extra":true}'
            with self.subTest(call=i), self.assertRaises(ValueError): self.match()
            self.rows = copy.deepcopy(original)
            self.rows[i+1]['data']['message']['content'][0]['text'] = '{"wrong":true}'
            with self.subTest(response=i), self.assertRaises(ValueError): self.match()

    def test_wrong_snapshot_token_input_reopen_budget_and_readback_denied(self):
        original = copy.deepcopy(self.rows)
        for index, key, value, response in [(4, 'snapshot_id', '2', False), (4, 'element_token', 'other', False),
            (4, 'element_index', True, False), (4, 'text', 'other', False), (8, 'snapshot_id', '1', False),
            (12, 'snapshot_id', '2', False), (13, 'used', 11, True), (17, 'used', True, True),
            (19, 'content', 'other', True)]:
            self.rows = copy.deepcopy(original)
            data = self.rows[index]['data']
            old = data['message']['content'][0]['text'] if response else data['arguments']
            changed = json.loads(old); changed[key] = value
            if response: data['message']['content'][0]['text'] = json.dumps(changed)
            else: data['arguments'] = json.dumps(changed)
            with self.subTest(index=index, key=key), self.assertRaises(ValueError): self.match()

    def test_pairing_order_duplicates_errors_and_parallel_dispatch_denied(self):
        original = copy.deepcopy(self.rows)
        for fault in ('id', 'name', 'error', 'duplicate', 'missing', 'parallel', 'seq'):
            self.rows = copy.deepcopy(original)
            if fault == 'id': self.rows[1]['data']['message']['toolCallId'] = 'other'
            elif fault == 'name': self.rows[4]['data']['name'] = 'vm_save'
            elif fault == 'error': self.rows[1]['data']['message']['isError'] = True
            elif fault == 'duplicate': self.rows.extend(copy.deepcopy(self.rows[-2:]))
            elif fault == 'missing': self.rows.pop()
            elif fault == 'parallel': self.rows[1], self.rows[2] = self.rows[2], self.rows[1]
            else: self.rows[2]['seq'] = True
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.match()

    def test_missing_fake_or_malformed_image_metadata_denied(self):
        original = copy.deepcopy(self.rows)
        for fault in ('missing', 'type', 'hash', 'bytes', 'width', 'format'):
            self.rows = copy.deepcopy(original)
            blocks = self.rows[3]['data']['message']['content']; attachment = blocks[1]['attachment']
            if fault == 'missing': blocks.pop()
            elif fault == 'type': blocks[1]['type'] = 'text'
            elif fault == 'hash': attachment['attachmentId'] = '/other'
            elif fault == 'bytes': attachment['bytes'] = True
            elif fault == 'width': attachment['width'] = 0
            else: attachment['mediaType'] = 'image/jpeg'
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.match()

    def test_guest_trace_is_reverified_not_trusted_by_status_label(self):
        self.fixture.rows[-2]['value'] = 'wrong readback'
        with self.assertRaises(ValueError): self.match()


if __name__ == '__main__': unittest.main()
