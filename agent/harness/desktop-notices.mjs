/** P6-only classification of reviewed official notices; preserves every row.
 * Templates/thresholds: DeepSeek MIT, see THIRD_PARTY_NOTICES.md.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

export const noticePolicy = JSON.parse(readFileSync(new URL('./desktop-notices.json', import.meta.url), 'utf8'));
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  return value;
}
export function reminderText(name, count, argumentsText) {
  if (count === noticePolicy.thresholds[0]) return noticePolicy.gentle;
  const cap = noticePolicy.previewChars;
  const preview = argumentsText.length > cap ? `${argumentsText.slice(0, cap)}… (+${argumentsText.length - cap} more chars)` : argumentsText;
  return noticePolicy.detailed.replace('{tool}', name).replace('{count}', String(count)).replace('{arguments}', preview);
}

export function classifyDesktopMessages(rows) {
  const users = rows.filter(row => row.type === 'user/message');
  const prompts = users.filter(row => row.data?.source?.kind === 'user');
  const notices = users.filter(row => row.data?.source?.kind !== 'user');
  if (!notices.length) return { prompts, frameworkNotices: 0, rawUserMessages: users.length };
  const events = rows.filter(row => row.type !== 'session');
  assert.ok(events.every((row, index) => Number.isInteger(row.seq) && (index === 0 || row.seq > events[index - 1].seq)));
  const calls = new Map(), completed = new Set(), pending = [];
  let chain = '', count = 0, accepted = 0;
  for (const row of events) {
    if (row.type === 'tool/call') {
      const data = row.data;
      assert.ok(typeof data?.callId === 'string' && !calls.has(data.callId));
      assert.ok(typeof data.name === 'string' && typeof data.arguments === 'string');
      let args;
      try { args = JSON.parse(data.arguments); } catch { args = data.arguments; }
      calls.set(data.callId, { name: data.name, argumentsText: JSON.stringify(canonical(args)) });
    } else if (row.type === 'tool/result') {
      const id = row.data?.message?.toolCallId;
      assert.ok(calls.has(id) && !completed.has(id));
      completed.add(id);
      const call = calls.get(id), key = JSON.stringify([call.name, call.argumentsText]);
      count = key === chain ? count + 1 : 1;
      chain = key;
      if (noticePolicy.tools.includes(call.name) && noticePolicy.thresholds.includes(count)) {
        pending.push({ source: { kind: noticePolicy.sourceKind, form: noticePolicy.form, summary: `${call.name} × ${count}` },
          content: [{ type: 'text', text: reminderText(call.name, count, call.argumentsText) }] });
      }
    } else if (row.type === 'user/message') {
      if (row.data?.source?.kind === 'user') { chain = ''; count = 0; pending.length = 0; continue; }
      const expected = pending.shift();
      assert.ok(expected, 'framework notice lacks completed repeated-call evidence');
      assert.equal(row.data?.role, 'user');
      assert.deepEqual(row.data.source, expected.source);
      assert.deepEqual(row.data.content, expected.content);
      accepted++;
    }
  }
  assert.equal(accepted, notices.length);
  return { prompts, frameworkNotices: accepted, rawUserMessages: users.length };
}
