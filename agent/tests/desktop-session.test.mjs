import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { realpathSync } from 'node:fs';
import { join } from 'node:path';
import { startDesktopSession, inspectDesktopSession, cancelDesktopSession } from '../harness/desktop-session.mjs';
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
  assert.equal((await inspectDesktopSession(f.root, f.rpc, f.readSession)).promptObserved, true);
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
    if (fault === 'prompt') assert.equal((await inspectDesktopSession(f.root, f.rpc, f.readSession)).promptObserved, true);
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
