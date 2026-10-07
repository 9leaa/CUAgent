import test from 'node:test';
import assert from 'node:assert/strict';
import { handoffPrompt, HANDOFF_TOOLS } from '../harness/handoff-prompt.mjs';

test('handoff prompt keeps GUI body, result transport and final object distinct', () => {
  const prompt = handoffPrompt({runId:'run', sessionId:'session', inputSha256:'a'.repeat(64)});
  for (const rule of ['vm_type.text传正文D', 'vm_write_result.value也传正文D',
    '绝不是HandoffResult JSON字符串', '最终助手消息才输出R的JSON',
    '不手动二次转义', '末尾恰好一个LF', 'vm_read_result应读到D加一个LF',
    'value必须为该观察原文D', '不再输入或保存', '不能重复观察并提交同一个错误值']) {
    assert.ok(prompt.includes(rule), rule);
  }
});

test('handoff prompt separates temporal progression from contradictory facts', () => {
  const prompt = handoffPrompt({runId:'run', sessionId:'session', inputSha256:'a'.repeat(64)});
  for (const rule of ['正常历史进展', '相同时间和范围', '日期或范围不足', '不修改CSV事实',
    '不能把计划当成果', '一个JSON对象', '原30次实际请求', '必须vm_reopen']) {
    assert.ok(prompt.includes(rule), rule);
  }
  assert.ok(prompt.includes('runId=run，sessionId=session，inputSha256=' + 'a'.repeat(64)));
  assert.equal(HANDOFF_TOOLS.length, 9);
  assert.ok(prompt.includes('vm_check_draft'));
  assert.ok(prompt.includes('输入后禁止再次预检或二次输入'));
  assert.ok(prompt.includes('vm_locate_quote'));
  assert.ok(prompt.includes('多义时不能默认选择首个'));
  assert.ok(!prompt.includes('rubric'));
  assert.ok(!prompt.includes('测试项目：订单审计交接'));
});
