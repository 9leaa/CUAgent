import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('daily', Path(__file__).parents[1] / 'daily_report.py')
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)
NOTE = '# 海港\n\n## 进展\n完成接口\n补充测试\n\n## 阻塞\n无\n\n## 下一步\n联调\n'
CSV = 'team,units,revenue\n"研发,一组",2,1.5\nB,-2,\nC,0,-0.5\n'


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'note.md').write_text(NOTE)
        (self.source / 'data.csv').write_text(CSV)
        self.spec = {'date': '2026-10-02', 'notes': ['note.md'],
                     'csv': [{'path': 'data.csv', 'numericColumns': ['units', 'revenue']}]}
        self.run = self.root / 'run'

    def prepare(self):
        (self.source / 'spec.json').write_text(json.dumps(self.spec))
        return daily.prepare(self.source / 'spec.json', self.run, renderer=False)

    def evidence(self):
        """Synthetic correlated events: unit test only, not real model evidence."""
        self.prepare()
        approval = json.loads((self.run / 'approval.json').read_text())
        oracle = json.loads((self.run / 'oracle.json').read_text())
        expected = oracle['expected']
        workspace = self.run / 'workspace'
        artifacts = {'report.json': json.dumps(expected, ensure_ascii=False), 'report.md': daily.markdown(expected)}
        for name, content in artifacts.items():
            (workspace / name).write_text(content)
        calls = [('workspace_read', {'path': 'inputs/note.md'},
                  {'path': 'inputs/note.md', 'sha256': daily.sha(NOTE), 'truncated': False, 'content': NOTE, 'bytes': len(NOTE.encode())}),
                 ('workspace_csv_stats', {'path': 'inputs/data.csv', 'numericColumns': ['units', 'revenue']}, expected['csv'][0])]
        for name, content in artifacts.items():
            value = {'path': name, 'bytes': len(content.encode()), 'sha256': daily.sha(content)}
            calls += [('workspace_write', {'path': name, 'content': content}, value),
                      ('workspace_read', {'path': name}, {**value, 'startLine': 1, 'truncated': False, 'content': content})]
        rows = [{'seq': 0, 'type': 'request/header', 'data': {'header': {'config': daily.MODEL,
                 'tools': [{'name': t} for t in daily.TOOLS]}}}]
        audit = []
        for used, (name, args, value) in enumerate(calls, 1):
            call_id = str(used)
            encoded = json.dumps(args, ensure_ascii=False, separators=(',', ':'))
            rows += [{'seq': len(rows), 'type': 'tool/call', 'data': {'callId': call_id, 'name': name, 'arguments': encoded}},
                     {'seq': len(rows) + 1, 'type': 'tool/result', 'data': {'message': {'toolCallId': call_id,
                      'isError': False, 'content': [{'type': 'text', 'text': json.dumps(value)}]}}}]
            common = {'runId': approval['runId'], 'sessionId': approval['sessionId'], 'callId': call_id, 'name': name}
            audit += [{**common, 'event': 'dispatch', 'used': used, 'arguments': {'sha256': daily.sha(encoded)}},
                      {**common, 'event': 'result', 'outcome': 'returned'}]
        rows.append({'seq': len(rows), 'type': 'turn/end', 'data': {'reason': {'kind': 'completed'}}})
        self.rows, self.audit = rows, audit
        self.persist()
        return expected

    def persist(self):
        (self.run / 'session.jsonl').write_text('\n'.join(map(json.dumps, self.rows)) + '\n')
        (self.run / 'audit/calls.jsonl').write_text('\n'.join(map(json.dumps, self.audit)) + '\n')

    def test_prepare_no_execution_outputs_and_private_oracle(self):
        self.prepare()
        self.assertFalse((self.run / 'workspace/report.json').exists())
        self.assertEqual((self.run / 'oracle.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.source / 'note.md').read_text(), NOTE)
        self.assertNotIn('expected', json.loads((self.run / 'workspace/task.json').read_text()))
        with self.assertRaises(ValueError):
            daily.prepare(self.source / 'spec.json', self.run)

    def test_independent_statistics_quotes_missing_negative_fraction(self):
        value = daily.csv_oracle('x.csv', CSV.encode(), ['units', 'revenue'])
        self.assertEqual(value['numeric']['units'], {'count': 3, 'missing': 0, 'sum': 0, 'min': -2, 'max': 2, 'mean': 0})
        self.assertEqual(value['numeric']['revenue'], {'count': 2, 'missing': 1, 'sum': 1, 'min': -0.5, 'max': 1.5, 'mean': 0.5})

    def test_note_preserves_multiline(self):
        value = daily.note_record('note.md', NOTE.encode())
        self.assertEqual(value['progress'], '完成接口\n补充测试')
        for invalid in [NOTE.replace('## 阻塞', '## 进展'), NOTE.replace('无', ''), NOTE.replace('## 下一步', '## 执行命令')]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                daily.note_record('note.md', invalid.encode())

    def test_reject_path_and_links_before_creating_run(self):
        for name in ['../note.md', '/tmp/note.md', 'sub/note.md']:
            self.spec['notes'] = [name]
            with self.assertRaises(ValueError):
                self.prepare()
        (self.source / 'linked.md').symlink_to(self.source / 'note.md')
        self.spec['notes'] = ['linked.md']
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.run.exists())

    def test_bad_csv_rejected(self):
        for data in ['a,a\n1,2\n', 'a,b\n1\n', 'a\nNaN\n', 'a\n1e999\n', 'a\n"open']:
            with self.subTest(data=data), self.assertRaises((ValueError, daily.csv.Error)):
                daily.csv_oracle('x.csv', data.encode(), ['a'])

    def test_boolean_is_not_numeric_statistics(self):
        self.assertFalse(daily.same({'count': True}, {'count': 1}))
        self.assertTrue(daily.same({'count': 1.0}, {'count': 1}))
        with self.assertRaisesRegex(ValueError, 'duplicate report field'):
            daily.report_json('{"count":99,"count":1}')

    def test_correlated_evidence_positive(self):
        self.evidence()
        self.assertEqual(daily.verify(self.run)['status'], 'SUCCEEDED')

    def test_renderer_requires_correlated_internal_read(self):
        self.evidence()
        config = json.loads((self.run / 'approval.json').read_text())
        config['allowedTools'] = daily.DAILY_TOOLS
        (self.run / 'approval.json').write_text(json.dumps(config))
        self.rows[0]['data']['header']['tools'] = [{'name': name} for name in daily.DAILY_TOOLS]
        call = next(r for r in self.rows if r['type'] == 'tool/call' and r['data']['callId'] == '5')
        call['data'].update(name='workspace_daily_report', arguments='{}')
        admitted = next(r for r in self.audit if r['event'] == 'dispatch' and r['callId'] == '5')
        done = next(r for r in self.audit if r['event'] == 'result' and r['callId'] == '5')
        admitted['name'] = done['name'] = 'workspace_daily_report'
        admitted['arguments']['sha256'] = daily.sha('{}')
        data = (self.run / 'workspace/report.json').read_bytes()
        common = {'runId': config['runId'], 'sessionId': config['sessionId'], 'callId': '5:daily-source', 'name': 'workspace_read'}
        child = {**common, 'event': 'dispatch', 'used': 6, 'arguments': {'sha256': daily.sha('{"path":"report.json"}')}}
        child_done = {**common, 'event': 'result', 'outcome': 'returned', 'artifact': {'bytes': len(data), 'sha256': daily.sha(data)}}
        position = self.audit.index(admitted) + 1
        self.audit[position:position] = [child, child_done]
        next(r for r in self.audit if r['event'] == 'dispatch' and r['callId'] == '6')['used'] = 7
        self.persist()
        self.assertEqual(daily.verify(self.run)['rawCalls'], 7)
        child_done['artifact']['sha256'] = '0' * 64
        self.persist()
        with self.assertRaisesRegex(ValueError, 'internal read evidence'):
            daily.verify(self.run)

    def test_content_changes_rejected_even_with_good_json(self):
        expected = self.evidence()
        path = self.run / 'workspace/report.md'
        path.write_text(path.read_text().replace('完成接口', '未完成接口'))
        with self.assertRaisesRegex(ValueError, 'Markdown'):
            daily.verify(self.run)
        path.write_text(daily.markdown(expected))
        expected['csv'][0]['numeric']['units']['sum'] = 100
        (self.run / 'workspace/report.json').write_text(json.dumps(expected))
        with self.assertRaisesRegex(ValueError, 'JSON'):
            daily.verify(self.run)

    def test_wrong_model_or_thinking_rejected(self):
        self.evidence()
        for change in [{'reasoningEffort': 'high'}, {'model': 'deepseek-v4-pro'}]:
            self.rows[0]['data']['header']['config'] = {**daily.MODEL, **change}
            self.persist()
            with self.assertRaisesRegex(ValueError, 'model/thinking'):
                daily.verify(self.run)

    def test_missing_result_readback_and_extra_tool_rejected(self):
        self.evidence()
        originals = copy.deepcopy(self.rows)
        self.rows = [r for r in self.rows if not (r['type'] == 'tool/result' and r['data']['message']['toolCallId'] == '6')]
        self.persist()
        with self.assertRaises(ValueError):
            daily.verify(self.run)
        self.rows = copy.deepcopy(originals)
        self.rows[0]['data']['header']['tools'].append({'name': 'bash'})
        self.persist()
        with self.assertRaisesRegex(ValueError, 'unexpected model tools'):
            daily.verify(self.run)

    def test_tampered_input_and_budget_rejected(self):
        self.evidence()
        self.audit[2]['used'] = 19
        self.persist()
        with self.assertRaisesRegex(ValueError, 'budget'):
            daily.verify(self.run)


if __name__ == '__main__':
    unittest.main()
