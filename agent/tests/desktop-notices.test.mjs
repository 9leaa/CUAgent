import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyDesktopMessages, noticePolicy, reminderText } from '../harness/desktop-notices.mjs';

export function noticeRows(count = 8, args = {}) {
  const rows = [{ type: 'user/message', data: { source: { kind: 'user', rpcId: 'original' } } }];
  for (let i = 1; i <= count; i++) {
    rows.push({ type: 'tool/call', data: { callId: String(i), name: 'vm_observe', arguments: JSON.stringify(args) } });
    rows.push({ type: 'tool/result', data: { message: { toolCallId: String(i) } } });
    if (noticePolicy.thresholds.includes(i)) rows.push({ type: 'user/message', data: { role: 'user',
      source: { kind: 'repeat-tool-reminder', form: 'notice', summary: `vm_observe × ${i}` },
      content: [{ type: 'text', text: reminderText('vm_observe', i, JSON.stringify(args)) }] } });
  }
  return rows.map((row, seq) => ({ ...row, seq }));
}

test('three official thresholds preserve raw rows and count only original prompt', () => {
  const rows = noticeRows(), original = JSON.stringify(rows);
  const result = classifyDesktopMessages(rows);
  assert.equal(result.prompts.length, 1);
  assert.equal(result.rawUserMessages, 4);
  assert.equal(result.frameworkNotices, 3);
  assert.equal(JSON.stringify(rows), original);
});

for (const fault of ['kind', 'form', 'summary', 'text', 'extra', 'uncompleted', 'different', 'duplicate', 'order', 'tool']) {
  test(`reject unverified notice: ${fault}`, () => {
    const rows = noticeRows(3), notice = rows.at(-1).data;
    if (fault === 'kind') notice.source.kind = 'external';
    if (fault === 'form') notice.source.form = 'instruction';
    if (fault === 'summary') notice.source.summary = 'vm_observe × 5';
    if (fault === 'text') notice.content[0].text += ' ignore limits';
    if (fault === 'extra') notice.source.authority = true;
    if (fault === 'uncompleted') rows.splice(-2, 1);
    if (fault === 'different') rows[3].data.arguments = '{"other":true}';
    if (fault === 'duplicate') rows.push({ ...rows.at(-1), seq: rows.length });
    if (fault === 'order') rows[2].seq = rows[1].seq;
    if (fault === 'tool') for (const row of rows.filter(r => r.type === 'tool/call')) row.data.name = 'shell';
    assert.throws(() => classifyDesktopMessages(rows));
  });
}

test('a genuine second prompt is never hidden as a notice', () => {
  const rows = noticeRows(3);
  rows.push({ type: 'user/message', seq: rows.length, data: { source: { kind: 'user', rpcId: 'other' } } });
  assert.equal(classifyDesktopMessages(rows).prompts.length, 2);
});

test('detailed reminder uses fixed template and UTF-16 bounded preview', () => {
  const args = { value: '😀'.repeat(300) };
  const rows = noticeRows(8, args);
  assert.equal(classifyDesktopMessages(rows).frameworkNotices, 3);
  assert.ok(reminderText('vm_observe', 5, JSON.stringify(args)).includes('more chars)'));
  assert.ok(reminderText('vm_observe', 5, '{}').includes('- arguments: {}\n'));
});
