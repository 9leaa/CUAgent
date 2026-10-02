import test from 'node:test';
import assert from 'node:assert/strict';
import { observedSession, assertUnstarted, reportPrompt, draftReportPrompt } from '../harness/daily-report-runner.mjs';

test('normal and scheduled prompts preserve the full CSV contract and write-once rule', () => {
  for (const prompt of [reportPrompt(), draftReportPrompt()]) {
    assert.ok(prompt.includes('path、rowCount、columnCount、columns、numeric、bytes、sha256'));
    assert.ok(prompt.includes('字段和值均来自对应真实工具返回'));
    assert.ok(prompt.includes('不覆盖任何文件'));
    assert.ok(prompt.includes('最多30次实际请求'));
  }
  assert.ok(draftReportPrompt().includes('禁止生成 report.md'));
  assert.ok(draftReportPrompt().includes('最后完整读回 report.json'));
  assert.ok(!draftReportPrompt().includes('随后调用 workspace_daily_report'));
});

test('first prompt recovery requires no local intent and no official work', () => {
  assert.doesNotThrow(() => assertUnstarted([{ type: 'session/header' }], false));
  assert.throws(() => assertUnstarted([], true), /already recorded/);
  for (const type of ['user/message', 'turn/start', 'tool/call', 'request/header']) {
    assert.throws(() => assertUnstarted([{ type }], false), /already contains work/);
  }
});

test('recovery observation matches exact official prompt identity without echoing content', () => {
  const rows = [{ type: 'turn/start', data: {} },
    { type: 'user/message', data: { source: { kind: 'user', rpcId: 'original' }, content: 'private' } },
    { type: 'tool/call', data: {} }, { type: 'turn/end', data: { reason: 'completed' } }];
  const observed = observedSession('session', false, rows, 'original');
  assert.equal(observed.promptObserved, true);
  assert.equal(observed.terminal, true);
  assert.equal(observed.calls, 1);
  assert.equal(JSON.stringify(observed).includes('private'), false);
  assert.equal(observedSession('session', false, rows, 'different').promptObserved, false);
  assert.equal(observedSession('session', true, rows, 'original').terminal, false);
});

test('old turn completion never certifies a later unfinished turn', () => {
  const rows = [{ type: 'turn/start', data: {} }, { type: 'turn/end', data: { reason: 'completed' } },
    { type: 'turn/start', data: {} }];
  assert.equal(observedSession('session', false, rows).terminal, false);
  assert.equal(observedSession('session', false, []).terminal, false);
  assert.equal(observedSession('session', false, []).promptObserved, false);
});
