import assert from 'node:assert/strict';
import test from 'node:test';
import { collectReportInputs } from '../report-inputs.mjs';

const task = () => ({ version: 1, date: '2026-10-03', workflow: 'renderer-v1',
  notes: ['inputs/note.md'], csv: [{ path: 'inputs/data.csv', numericColumns: ['n'] }] });
const read = (path, content) => ({ path, content, bytes: Buffer.byteLength(content), sha256: 'a'.repeat(64), truncated: false });
function fixture(spec = task(), hook = () => {}) {
  const seen = [], controller = new AbortController();
  const invoke = async (name, args, sequence) => {
    seen.push({ name, args, sequence });
    const override = hook({ name, args, sequence, controller });
    if (override !== undefined) return override;
    if (name === 'workspace_read') return read(args.path, args.path === 'task.json' ? JSON.stringify(spec) : '# raw note');
    return { path: args.path, rowCount: 1, columnCount: 1, columns: ['n'], numeric: { n: {} }, bytes: 4, sha256: 'b'.repeat(64) };
  };
  return { seen, controller, run: () => collectReportInputs({ invoke, signal: controller.signal }) };
}

test('aggregate preserves full source and CSV object using separately sequenced invocations', async () => {
  const f = fixture(), result = await f.run();
  assert.equal(result.notes[0].content, '# raw note');
  assert.deepEqual(result.csv[0].columns, ['n']);
  assert.deepEqual(f.seen.map(x => [x.name, x.sequence]), [['workspace_read', 1], ['workspace_read', 2], ['workspace_csv_stats', 3]]);
  assert.deepEqual(f.seen[2].args, task().csv[0]);
});

test('invalid or escaping task rejects before reading listed inputs', async () => {
  for (const mutate of [t => t.notes.push(t.notes[0]), t => t.notes[0] = '../secret.md',
    t => t.notes[0] = '/secret.md', t => t.csv[0].numericColumns.push('n'),
    t => t.extra = true, t => t.date = '2026-02-30', t => t.csv = [], t => t.workflow = 'unknown']) {
    const spec = task(); mutate(spec); const f = fixture(spec);
    await assert.rejects(f.run(), { code: 'INVALID_TASK' });
    assert.equal(f.seen.length, 1);
  }
});

test('cancel before and between internal calls prevents subsequent invocation', async () => {
  const before = fixture(); before.controller.abort();
  await assert.rejects(before.run()); assert.equal(before.seen.length, 0);
  const between = fixture(task(), ({ sequence, controller }) => { if (sequence === 2) controller.abort(); });
  await assert.rejects(between.run()); assert.equal(between.seen.length, 2);
});

test('internal budget or path refusal propagates without retry or later calls', async () => {
  for (const code of ['BUDGET_EXHAUSTED', 'PATH_ESCAPE', 'POLICY_UNAVAILABLE']) {
    const f = fixture(task(), ({ sequence }) => { if (sequence === 2) throw Object.assign(new Error(code), { code }); });
    await assert.rejects(f.run(), { code }); assert.equal(f.seen.length, 2);
  }
});

test('truncated or malformed source cannot masquerade as full input', async () => {
  for (const value of [ { ...read('task.json', '{}'), truncated: true }, read('wrong.json', '{}'), read('task.json', 'not json') ]) {
    const f = fixture(task(), () => value);
    await assert.rejects(f.run()); assert.equal(f.seen.length, 1);
  }
});

test('oversize output and omitted CSV fields are rejected, never silently truncated', async () => {
  const big = fixture(task(), ({ sequence }) => sequence === 3 ? {
    path: 'inputs/data.csv', rowCount: 1, columnCount: 1, columns: ['x'.repeat(65536)],
    numeric: {}, bytes: 1, sha256: 'a'.repeat(64) } : undefined);
  await assert.rejects(big.run(), { code: 'OUTPUT_TOO_LARGE' });
  const missing = fixture(task(), ({ sequence }) => sequence === 3 ? { rowCount: 1 } : undefined);
  await assert.rejects(missing.run(), { code: 'INCOMPLETE_INPUT' });
});
