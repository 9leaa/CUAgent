import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { realpathSync, writeFileSync, chmodSync } from 'node:fs';
import { join } from 'node:path';
import { startDesktopSession, startHandoffSession, inspectDesktopSession, cancelDesktopSession } from '../harness/desktop-session.mjs';
import { HANDOFF_TOOLS, handoffTools } from '../harness/handoff-prompt.mjs';
import { DAILY_MODEL } from '../harness/daily-report-runner.mjs';

function fixture(t, fault) {
  const root = realpathSync(mkdtempSync(join(tmpdir(), 'cuagent-session-')));
  t.after(() => rmSync(root, { recursive: true }));
  mkdirSync(join(root, 'workspace'), { mode: 0o700 });
  const binding = { runId: 'p2-11111111-1111-4111-8111-111111111111',
    sessionId: 'session-22222222-2222-4222-8222-222222222222', cwd: join(root, 'workspace'), lines: ['交接内容', 'Next step'] };
  const calls = [];
  let created = false, running = false, rows = [];
  const rpc = async (method, args) => {
    calls.push({ method, args });
    if (method === 'session/list') return { items: created ? [{ sessionId: binding.sessionId, cwd: binding.cwd, running }] : [] };
    if (method === 'agentPresets/list') return { presets: [{ id: fault === 'preset' ? 'standard' : 'real-app' }] };
    if (method === 'session/modelCatalog') return { groups: [{ id: DAILY_MODEL.provider,
      models: [{ id: DAILY_MODEL.model, name: 'DeepSeek-V41-Flash', reasoning: { efforts: [{ id: 'off' }] } }] }] };
    if (method === 'session/create') {
      assert.ok(existsSync(join(root, 'create-request.json')));
      created = true;
      if (fault === 'create') throw Error('lost create acknowledgement');
      return { sessionId: binding.sessionId };
    }
    if (method === 'session/selectModel') {
      assert.ok(existsSync(join(root, 'model-select-request.json')));
      return { selected: { ...DAILY_MODEL, ...(fault === 'model' ? { reasoningEffort: 'high' } : {}) } };
    }
    if (method === 'session/prompt') {
      assert.ok(existsSync(join(root, 'prompt-request.json')));
      running = true;
      rows = [{ type: 'user/message', data: { source: { kind: 'user', rpcId: args.request.requestId } } }, { type: 'turn/start' }];
      if (fault === 'prompt') throw Error('lost prompt acknowledgement');
      return { accepted: true };
    }
    if (method === 'session/cancel') {
      running = false;
      rows.push({ type: 'turn/end', data: { reason: 'aborted' } });
      return { ok: true };
    }
    throw Error('unexpected RPC');
  };
  return { root, binding, rpc, calls, readSession: async () => rows };
}

test('fixed official model/off, intent before RPC, original inspection and cancel once', async t => {
  const f = fixture(t);
  const result = await startDesktopSession(f.root, f.binding, f.rpc);
  assert.equal(result.accepted, true);
  assert.deepEqual(result.model, DAILY_MODEL);
  const request = JSON.parse(readFileSync(join(f.root, 'prompt-request.json'))).request;
  assert.ok(request.content[0].text.includes(JSON.stringify(f.binding.lines)));
  assert.equal((await inspectDesktopSession(f.root, f.rpc, f.readSession)).evidencePending, true);
  assert.equal((await cancelDesktopSession(f.root, f.rpc, f.readSession)).cancelRequested, true);
  assert.equal((await inspectDesktopSession(f.root, f.rpc, f.readSession)).terminal, true);
  assert.equal((await cancelDesktopSession(f.root, f.rpc, f.readSession)).cancelRequested, false);
  assert.equal(f.calls.filter(c => c.method === 'session/cancel').length, 1);
  await assert.rejects(startDesktopSession(f.root, f.binding, f.rpc));
  assert.equal(f.calls.filter(c => c.method === 'session/create').length, 1);
});

for (const fault of ['create', 'model', 'prompt', 'preset']) {
  test(`failure ${fault} cannot re-create or re-send`, async t => {
    const f = fixture(t, fault);
    await assert.rejects(startDesktopSession(f.root, f.binding, f.rpc));
    const count = f.calls.length;
    await assert.rejects(startDesktopSession(f.root, f.binding, f.rpc));
    assert.equal(f.calls.length, count);
    assert.ok(f.calls.filter(c => c.method === 'session/prompt').length <= 1);
    if (fault === 'prompt') assert.equal((await inspectDesktopSession(f.root, f.rpc, f.readSession)).evidencePending, true);
  });
}

test('invalid input has no RPC or intent', async t => {
  const f = fixture(t);
  for (const patch of [{ lines: ['a\nb'] }, { lines: ['x'.repeat(4096)] }, { lines: [false] },
    { cwd: '/outside' }, { runId: '../escape' }, { tool: 'shell' }]) {
    await assert.rejects(startDesktopSession(f.root, { ...f.binding, ...patch }, f.rpc));
  }
  assert.equal(f.calls.length, 0);
  assert.equal(existsSync(join(f.root, 'create-request.json')), false);
});

function handoffFixture(t, fault) {
  const f = fixture(t, fault), originalRpc = f.rpc;
  const { lines, ...base } = f.binding;
  f.binding = { ...base, kind: 'project-handoff', inputSha256: 'a'.repeat(64) };
  f.ready = { runId: base.runId, kind: 'project-handoff', inputSha256: f.binding.inputSha256, toolNames: HANDOFF_TOOLS };
  writeFileSync(join(f.root, 'vm-tools-ready.json'), JSON.stringify(f.ready), { mode: 0o600 });
  f.rpc = async (method, args) => {
    if (method === 'agentPresets/list') {
      f.calls.push({ method, args });
      return { presets: [{ id: fault === 'preset' ? 'real-app' : 'project-handoff' }] };
    }
    return originalRpc(method, args);
  };
  return f;
}

for (const fault of ['none','tools','missing_mode','wrong_mode','no_protocol','binding_mode']) {
  test(`checked input creation ${fault} binds mode before any RPC`, async t => {
    const f = handoffFixture(t);
    Object.assign(f.binding,{protocol:'p7-tool-submit-v1',inputMode:'checked-draft-v1'});
    Object.assign(f.ready,{protocol:f.binding.protocol,inputMode:f.binding.inputMode,sessionId:f.binding.sessionId,
      toolNames:handoffTools(f.binding.protocol,f.binding.inputMode)});
    if (fault==='tools') f.ready.toolNames=handoffTools(f.binding.protocol);
    if (fault==='missing_mode') delete f.ready.inputMode;
    if (fault==='wrong_mode') f.ready.inputMode='literal-text';
    if (fault==='no_protocol') delete f.binding.protocol;
    if (fault==='binding_mode') f.binding.inputMode='literal-text';
    writeFileSync(join(f.root,'vm-tools-ready.json'),JSON.stringify(f.ready));
    if (fault!=='none') {
      await assert.rejects(startHandoffSession(f.root,f.binding,f.rpc));
      assert.equal(f.calls.length,0); assert.equal(existsSync(join(f.root,'desktop-session-binding.json')),false);
      return;
    }
    assert.equal((await startHandoffSession(f.root,f.binding,f.rpc)).accepted,true);
    assert.deepEqual(JSON.parse(readFileSync(join(f.root,'desktop-session-binding.json'),'utf8')),f.binding);
    assert.ok(f.calls.find(c=>c.method==='session/prompt').args.request.content[0].text.includes('不要重抄正文'));
    await assert.rejects(startHandoffSession(f.root,f.binding,f.rpc));
    assert.equal(f.calls.filter(c=>c.method==='session/prompt').length,1);
  });
}

for (const fault of ['none', 'legacy_tools', 'wrong_session', 'missing_protocol', 'unknown_protocol']) {
  test(`new submission creation binding ${fault} stays explicit and one-shot`, async t => {
    const f = handoffFixture(t);
    f.binding.protocol = 'p7-tool-submit-v1';
    f.ready = {...f.ready, protocol:f.binding.protocol, sessionId:f.binding.sessionId,
      toolNames:handoffTools(f.binding.protocol)};
    if (fault === 'legacy_tools') f.ready.toolNames = HANDOFF_TOOLS;
    if (fault === 'wrong_session') f.ready.sessionId = 'session-33333333-3333-3333-3333-333333333333';
    if (fault === 'missing_protocol') delete f.ready.protocol;
    if (fault === 'unknown_protocol') f.binding.protocol = 'unknown';
    writeFileSync(join(f.root, 'vm-tools-ready.json'), JSON.stringify(f.ready));
    if (fault !== 'none') {
      await assert.rejects(startHandoffSession(f.root, f.binding, f.rpc));
      assert.equal(f.calls.length, 0); assert.equal(existsSync(join(f.root, 'desktop-session-binding.json')), false);
      return;
    }
    assert.equal((await startHandoffSession(f.root, f.binding, f.rpc)).accepted, true);
    const saved = JSON.parse(readFileSync(join(f.root, 'desktop-session-binding.json'), 'utf8'));
    assert.deepEqual(saved, f.binding);
    const prompt = f.calls.find(call => call.method === 'session/prompt').args.request.content[0].text;
    assert.ok(prompt.includes('vm_submit_handoff({report:R})'));
    await assert.rejects(startHandoffSession(f.root, f.binding, f.rpc));
    assert.equal(f.calls.filter(call => call.method === 'session/prompt').length, 1);
  });
}

test('P7 uses source-bound analysis prompt, exact preset and original Flash/off lifecycle', async t => {
  const f = handoffFixture(t);
  assert.equal((await startHandoffSession(f.root, f.binding, f.rpc)).accepted, true);
  const create = f.calls.find(call => call.method === 'session/create');
  assert.equal(create.args.request.agentPreset, 'project-handoff');
  const prompt = f.calls.find(call => call.method === 'session/prompt').args.request.content[0].text;
  for (const value of [f.binding.runId, f.binding.sessionId, f.binding.inputSha256, 'vm_read_materials', 'vm_reopen', 'sourceHashes', 'JSON schema']) assert.ok(prompt.includes(value));
  assert.ok(!prompt.includes('文本数据：'));
  assert.deepEqual(f.calls.find(call => call.method === 'session/selectModel').args.request, { sessionId: f.binding.sessionId, ...DAILY_MODEL });
  assert.equal((await inspectDesktopSession(f.root, f.rpc, f.readSession)).evidencePending, true);
  assert.equal((await cancelDesktopSession(f.root, f.rpc, f.readSession)).cancelRequested, true);
  await assert.rejects(startHandoffSession(f.root, f.binding, f.rpc));
  assert.equal(f.calls.filter(call => call.method === 'session/prompt').length, 1);
});

for (const fault of ['preset', 'model', 'create', 'prompt']) test(`P7 ${fault} failure cannot replay or downgrade`, async t => {
  const f = handoffFixture(t, fault);
  await assert.rejects(startHandoffSession(f.root, f.binding, f.rpc));
  const count = f.calls.length;
  await assert.rejects(startHandoffSession(f.root, f.binding, f.rpc));
  assert.equal(f.calls.length, count);
  if (fault !== 'prompt') assert.equal(f.calls.filter(call => call.method === 'session/prompt').length, 0);
});

for (const mode of ['six_tools', 'wrong_input', 'extra_tool', 'public_ready', 'extra_lines', 'bad_session']) test(`P7 preflight rejects ${mode} before any RPC`, async t => {
  const f = handoffFixture(t);
  if (mode === 'six_tools') f.ready.toolNames = HANDOFF_TOOLS.filter(name => name !== 'vm_reopen');
  if (mode === 'wrong_input') f.ready.inputSha256 = 'b'.repeat(64);
  if (mode === 'extra_tool') f.ready.toolNames = [...HANDOFF_TOOLS, 'shell'];
  if (mode === 'extra_lines') f.binding.lines = ['prewritten answer'];
  if (mode === 'bad_session') f.binding.sessionId = 'session-not-uuid';
  writeFileSync(join(f.root, 'vm-tools-ready.json'), JSON.stringify(f.ready));
  if (mode === 'public_ready') chmodSync(join(f.root, 'vm-tools-ready.json'), 0o644);
  await assert.rejects(startHandoffSession(f.root, f.binding, f.rpc));
  assert.equal(f.calls.length, 0);
  assert.equal(existsSync(join(f.root, 'desktop-session-binding.json')), false);
});
