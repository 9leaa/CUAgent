import copy
import json
import unittest
import test_handoff_trace as trace_fixture
import test_handoff_exchanges as exchange_fixture


class QuoteEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.f = trace_fixture.HandoffTraceTests(); self.addCleanup(self.f.doCleanups)
        self.f.quote_args = [dict(sourceId='notes/n',quote='🙂')]
        self.f.setUp()
        self.e = exchange_fixture.HandoffExchangeTests(); self.addCleanup(self.e.doCleanups)
        self.e.execution_fixture = self.f; self.e.setUp()

    def test_real_producer_matches_both_logs(self):
        result = self.e.match()
        self.assertEqual((result['officialToolCalls'],result['rawCalls']),(11,16))
        self.assertFalse(result['sessionVerified'])

    def test_forged_offsets_hash_used_status_and_args_refused(self):
        original = copy.deepcopy(self.f.rows)
        for fault in ('offset','hash','used','status','argument','duplicate','missing','orphan'):
            self.f.rows = copy.deepcopy(original)
            response = self.f.result('locate_quote')['value']
            args = self.f.event('helper_arguments')
            if fault == 'offset': response['matches'][0]['start'] = 0
            if fault == 'hash': response['sourceSha256'] = '0'*64
            if fault == 'used': response['used'] = True
            if fault == 'status': response['status'] = 'NOT_FOUND'
            if fault == 'argument': args['args']['quote'] = 'different'
            if fault == 'duplicate': self.f.rows.insert(self.f.rows.index(args),copy.deepcopy(args))
            if fault == 'missing': self.f.rows.remove(args)
            if fault == 'orphan': args['call_id'] = 'other'
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.f.verify()

    def test_official_response_or_arguments_must_match_original_guest(self):
        original = copy.deepcopy(self.e.rows)
        for side in ('args','response'):
            self.e.rows = copy.deepcopy(original)
            call = next(r for r in self.e.rows if r['type']=='tool/call' and r['data']['name']=='vm_locate_quote')
            if side == 'args': call['data']['arguments'] = json.dumps(dict(sourceId='notes/n',quote='wrong'))
            else:
                response = self.e.rows[self.e.rows.index(call)+1]
                response['data']['message']['content'][0]['text'] = '{}'
            with self.subTest(side=side), self.assertRaises(ValueError): self.e.match()

    def test_not_found_unknown_source_and_ambiguous_results_recomputed(self):
        for args in (dict(sourceId='notes/n',quote='missing'),
                     dict(sourceId='../private',quote='x'),
                     dict(sourceId='notes/n',quote='a')):
            f = trace_fixture.HandoffTraceTests(); self.addCleanup(f.doCleanups)
            source = json.loads(self.f.materials)
            source['notes'][0]['content'] = 'a'*20
            f.material_bytes = json.dumps(source,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            f.quote_args = [args]; f.setUp()
            self.assertEqual(f.verify()['rawCalls'],16)
            f.result('locate_quote')['value']['truncated'] = not f.result('locate_quote')['value']['truncated']
            with self.assertRaises(ValueError): f.verify()


if __name__ == '__main__': unittest.main()
