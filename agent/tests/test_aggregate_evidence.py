"""Synthetic aggregate evidence. No model or official registry calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from agent.aggregate_evidence import verify_inputs
from agent.daily_report import prepare, sha, verify, markdown, MODEL, AGGREGATE_TOOLS


class AggregateEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / 'n.md').write_text('# N\n\n## 进展\nDone\n\n## 阻塞\n无\n\n## 下一步\nTest\n')
        (root / 'm.csv').write_text('n\n2\n4\n')
        (root / 'spec.json').write_text(json.dumps({'date': '2026-10-03', 'notes': ['n.md'], 'csv': [{'path': 'm.csv', 'numericColumns': ['n']}]}))
        prepare(root / 'spec.json', root / 'run', aggregate=True)
        self.workspace = root / 'run/workspace'
        self.oracle = json.loads((root / 'run/oracle.json').read_text())
        def read(path):
            data = (self.workspace / path).read_bytes()
            return dict(path=path, content=data.decode(), bytes=len(data), sha256=sha(data), startLine=1, truncated=False)
        self.parent = dict(name='workspace_report_inputs', args={}, callId='outer', seq=1, end=2,
                           value=dict(task=read('task.json'), notes=[read('inputs/n.md')], csv=copy.deepcopy(self.oracle['expected']['csv'])))
        self.audit = [dict(event='dispatch', callId='outer', name='workspace_report_inputs')]
        specs = [('workspace_read', {'path': 'task.json'}), ('workspace_read', {'path': 'inputs/n.md'}),
                 ('workspace_csv_stats', {'path': 'inputs/m.csv', 'numericColumns': ['n']})]
        for i, (name, args) in enumerate(specs, 1):
            encoded = json.dumps(args, separators=(',', ':'))
            data = (self.workspace / args['path']).read_bytes()
            common = dict(callId='outer:input-'+str(i), name=name)
            self.audit.append(dict(common, event='dispatch', arguments=dict(bytes=len(encoded.encode()), sha256=sha(encoded))))
            self.audit.append(dict(common, event='result', outcome='returned', artifact=dict(bytes=len(data), sha256=sha(data))))
        self.audit.append(dict(event='result', callId='outer', name='workspace_report_inputs', outcome='returned'))

    def verify(self):
        return verify_inputs(self.parent, self.audit, self.workspace, self.oracle)

    def test_proven_reads_preserve_complete_original_data(self):
        observations = self.verify()
        self.assertEqual(len(observations), 3)
        self.assertEqual(observations[-1]['value']['numeric']['n']['sum'], 6)

    def test_missing_extra_duplicate_or_reordered_children_rejected(self):
        original = copy.deepcopy(self.audit)
        for kind in ('missing', 'extra', 'duplicate', 'order'):
            self.audit = copy.deepcopy(original)
            if kind == 'missing': self.audit.pop(2)
            if kind == 'extra': self.audit.append(dict(event='dispatch', callId='outer:input-4', name='workspace_read'))
            if kind == 'duplicate': self.audit.append(self.audit[1])
            if kind == 'order': self.audit[1], self.audit[2] = self.audit[2], self.audit[1]
            with self.assertRaises(ValueError): self.verify()

    def test_false_statistics_truncation_and_changed_content_rejected(self):
        original = copy.deepcopy(self.parent)
        for kind in ('stats', 'truncated', 'content', 'args'):
            self.parent = copy.deepcopy(original)
            if kind == 'stats': self.parent['value']['csv'][0]['numeric']['n']['sum'] = 999
            if kind == 'truncated': self.parent['value']['notes'][0]['truncated'] = True
            if kind == 'content': self.parent['value']['notes'][0]['content'] = 'fake'
            if kind == 'args': self.parent['args'] = {'path': '/foreign'}
            with self.assertRaises(ValueError): self.verify()

    def test_failed_or_forged_audit_result_rejected(self):
        original = copy.deepcopy(self.audit)
        for kind in ('failed', 'artifact', 'arguments'):
            self.audit = copy.deepcopy(original)
            if kind == 'failed': self.audit[2]['outcome'] = 'error'
            if kind == 'artifact': self.audit[2]['artifact']['sha256'] = 'f'*64
            if kind == 'arguments': self.audit[1]['arguments']['bytes'] += 1
            with self.assertRaises(ValueError): self.verify()

    def test_source_mutation_rejected(self):
        (self.workspace / 'inputs/n.md').chmod(0o600)
        (self.workspace / 'inputs/n.md').write_text('changed')
        with self.assertRaises(ValueError): self.verify()

    def test_complete_verifier_requires_opt_in_and_all_aggregate_evidence(self):
        run = self.workspace.parent
        approval = json.loads((run / 'approval.json').read_text())
        expected = self.oracle['expected']
        json_text, md_text = json.dumps(expected, ensure_ascii=False), markdown(expected)
        (self.workspace / 'report.json').write_text(json_text)
        (self.workspace / 'report.md').write_text(md_text)
        def artifact(path, text):
            return dict(path=path, bytes=len(text.encode()), sha256=sha(text))
        json_meta, md_meta = artifact('report.json', json_text), artifact('report.md', md_text)
        calls = [('outer', 'workspace_report_inputs', {}, self.parent['value']),
                 ('write', 'workspace_write', {'path': 'report.json', 'content': json_text}, json_meta),
                 ('render', 'workspace_daily_report', {}, md_meta),
                 ('read-json', 'workspace_read', {'path': 'report.json'}, dict(json_meta, content=json_text, startLine=1, truncated=False)),
                 ('read-md', 'workspace_read', {'path': 'report.md'}, dict(md_meta, content=md_text, startLine=1, truncated=False))]
        rows = [dict(seq=0, type='request/header', data={'header': {'config': MODEL, 'tools': [{'name': n} for n in AGGREGATE_TOOLS]}})]
        audit = []
        for cid, name, args, value in calls:
            encoded = json.dumps(args, ensure_ascii=False, separators=(',', ':'))
            rows.append(dict(seq=len(rows), type='tool/call', data=dict(callId=cid, name=name, arguments=encoded)))
            rows.append(dict(seq=len(rows), type='tool/result', data={'message': {'toolCallId': cid, 'isError': False,
                         'content': [{'type': 'text', 'text': json.dumps(value)}]}}))
            audit.append(dict(event='dispatch', callId=cid, name=name, arguments=dict(bytes=len(encoded.encode()), sha256=sha(encoded))))
            if cid == 'outer': audit.extend(copy.deepcopy(self.audit[1:-1]))
            if cid == 'render':
                args_text = '{"path":"report.json"}'
                audit.extend([dict(event='dispatch', callId='render:daily-source', name='workspace_read', arguments={'sha256': sha(args_text)}),
                              dict(event='result', callId='render:daily-source', name='workspace_read', outcome='returned',
                                   artifact={'bytes': json_meta['bytes'], 'sha256': json_meta['sha256']})])
            audit.append(dict(event='result', callId=cid, name=name, outcome='returned'))
        rows.append(dict(seq=len(rows), type='turn/end', data={'reason': {'kind': 'completed'}}))
        count = 0
        for event in audit:
            event.update(runId=approval['runId'], sessionId=approval['sessionId'])
            if event['event'] == 'dispatch':
                count += 1; event['used'] = count
        def persist():
            (run / 'session.jsonl').write_text('\n'.join(map(json.dumps, rows))+'\n')
            Path(approval['ledgerPath']).write_text('\n'.join(map(json.dumps, audit))+'\n')
        persist()
        result = verify(run, aggregate=True)
        self.assertEqual((result['status'], result['calls'], result['rawCalls']), ('SUCCEEDED', 5, 9))
        with self.assertRaises(ValueError): verify(run)
        with self.assertRaises(ValueError): verify(run, aggregate=True, continuation=True)
        for mode in ('missing-child', 'wrong-stats', 'missing-readback'):
            original_rows, original_audit = copy.deepcopy(rows), copy.deepcopy(audit)
            if mode == 'missing-child': audit.pop(2)
            if mode == 'wrong-stats':
                value = json.loads(rows[2]['data']['message']['content'][0]['text'])
                value['csv'][0]['numeric']['n']['sum'] = 999
                rows[2]['data']['message']['content'][0]['text'] = json.dumps(value)
            if mode == 'missing-readback':
                value = json.loads(rows[-2]['data']['message']['content'][0]['text']); value['truncated'] = True
                rows[-2]['data']['message']['content'][0]['text'] = json.dumps(value)
            persist()
            with self.assertRaises(ValueError): verify(run, aggregate=True)
            rows, audit = original_rows, original_audit
