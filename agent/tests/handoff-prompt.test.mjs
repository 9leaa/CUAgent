import test from 'node:test';
import assert from 'node:assert/strict';
import { handoffPrompt, HANDOFF_TOOLS } from '../harness/handoff-prompt.mjs';

test('handoff prompt separates temporal progression from contradictory facts', () => {
  const prompt = handoffPrompt({runId:'run', sessionId:'session', inputSha256:'a'.repeat(64)});
  for (const rule of ['正常历史进展', '相同时间和范围', '日期或范围不足', '不修改CSV事实',
    '不能把计划当成果', '一个JSON对象', '原30次实际请求', '必须vm_reopen']) {
    assert.ok(prompt.includes(rule), rule);
  }
  assert.ok(prompt.includes('runId=run，sessionId=session，inputSha256=' + 'a'.repeat(64)));
  assert.equal(HANDOFF_TOOLS.length, 7);
  assert.ok(!prompt.includes('rubric'));
  assert.ok(!prompt.includes('测试项目：订单审计交接'));
});
