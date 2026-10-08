import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { handoffPrompt, HANDOFF_TOOLS, handoffTools } from '../harness/handoff-prompt.mjs';

test('explicit new protocol uses full report submission, no final-text contract or retries', () => {
  const binding = {runId:'run', sessionId:'session', inputSha256:'a'.repeat(64)};
  const prompt = handoffPrompt({...binding, protocol:'p7-tool-submit-v1'});
  assert.ok(prompt.startsWith('可信任务完成协议：p7-tool-submit-v1。'));
  for (const rule of ['唯一参数report传完整同一对象R', 'vm_submit_handoff({report:R})',
    '不得在两者之间插入其他工具', '普通文本不能代替提交', '不能重试、换会话',
    'read_result和submit_handoff预算', '原30次实际请求']) assert.ok(prompt.includes(rule), rule);
  for (const old of ['最终助手消息才输出R的JSON', '最终回复只输出同一个HandoffResult JSON']) assert.ok(!prompt.includes(old));
  assert.equal(handoffTools('p7-tool-submit-v1').length, 10);
  assert.equal(handoffTools().length, 9);
  assert.throws(() => handoffPrompt({...binding, protocol:'unknown'}));
});

test('preset completion instruction is conditional on bound protocol, never unconditionally final JSON', () => {
  const template = readFileSync(new URL('../harness/cordis.desktop.handoff.patch.yml', import.meta.url), 'utf8');
  assert.ok(template.includes('Follow the completion protocol explicitly bound in the task request'));
  assert.ok(template.includes('For p7-tool-submit-v1, submit the complete unchanged report object using vm_submit_handoff'));
  assert.ok(template.includes('For legacy-final-json (the default when no protocol is specified)'));
  assert.ok(!template.includes('End with only the required source-bound HandoffResult JSON.'));
  assert.ok(template.includes('no retry after uncertainty'));
});

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
