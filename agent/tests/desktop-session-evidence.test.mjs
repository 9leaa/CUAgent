import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, realpathSync, rmSync, writeFileSync, readFileSync, symlinkSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { officialSessionReader, inspectAndArchiveDesktopSession } from '../harness/desktop-session-evidence.mjs';
import { sessionCommand } from '../harness/desktop-session-command.mjs';
import { noticePolicy } from '../harness/desktop-notices.mjs';

function fixture(t) {
  const home = realpathSync(mkdtempSync(join(tmpdir(), 'cuagent-evidence-')));
  t.after(() => rmSync(home, { recursive: true }));
  const id = 'session-22222222-2222-4222-8222-222222222222';
  const directory = join(home, 'sessions', 'group', id);
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const target = join(directory, 'session.v4.jsonl.zstd');
  const rows = [{ type: 'user/message', data: { source: { kind: 'user', rpcId: 'original' } } },
    { type: 'turn/start' }, { type: 'turn/end', data: { reason: 'completed' } }];
  const raw = rows.map(row => JSON.stringify(row)).join('\n') + '\n';
  writeFileSync(target, execFileSync('/opt/homebrew/bin/zstd', ['-q', '-c'], { input: raw }), { mode: 0o600 });
  const root = join(home, 'run'); mkdirSync(root, { mode: 0o700 });
  const cwd = join(root, 'workspace'); mkdirSync(cwd);
  writeFileSync(join(root, 'desktop-session-binding.json'), JSON.stringify({ sessionId: id, cwd }));
  writeFileSync(join(root, 'prompt-request.json'), JSON.stringify({ request: { requestId: 'original' } }));
  const rpc = async () => ({ items: [{ sessionId: id, cwd, running: false }] });
  return { home, root, id, target, raw, rpc, reader: officialSessionReader(home) };
}

test('real zstd decode preserves original terminal JSONL bytes without modifying source', async t => {
  const f = fixture(t), before = readFileSync(f.target);
  assert.equal(f.reader(f.id).raw, f.raw);
  assert.equal((await inspectAndArchiveDesktopSession(f.root, f.rpc, f.reader)).terminal, true);
  assert.equal(readFileSync(join(f.root, 'session.jsonl'), 'utf8'), f.raw);
  await inspectAndArchiveDesktopSession(f.root, f.rpc, f.reader);
  assert.deepEqual(readFileSync(f.target), before);
});

test('duplicate session, traversal and linked source are rejected', t => {
  const f = fixture(t);
  assert.throws(() => f.reader('../session'));
  const duplicate = join(f.home, 'sessions', 'other', f.id);
  mkdirSync(duplicate, { recursive: true });
  const file = join(duplicate, 'session.v4.jsonl.zstd');
  writeFileSync(file, readFileSync(f.target));
  assert.throws(() => f.reader(f.id));
  rmSync(file); symlinkSync(f.target, file);
  assert.throws(() => f.reader(f.id));
});

test('nonterminal and unbound terminal evidence cannot become archived success', async t => {
  const f = fixture(t);
  const running = async () => ({ items: [{ sessionId: f.id, cwd: join(f.root, 'workspace'), running: true }] });
  assert.equal((await inspectAndArchiveDesktopSession(f.root, running, f.reader)).terminal, false);
  assert.equal(existsSync(join(f.root, 'session.jsonl')), false);
  writeFileSync(join(f.root, 'prompt-request.json'), JSON.stringify({ request: { requestId: 'other' } }));
  await assert.rejects(inspectAndArchiveDesktopSession(f.root, f.rpc, f.reader));
});

test('changed terminal bytes never overwrite the original archive', async t => {
  const f = fixture(t);
  await inspectAndArchiveDesktopSession(f.root, f.rpc, f.reader);
  const original = readFileSync(join(f.root, 'session.jsonl'));
  const changed = () => ({ ...f.reader(f.id), raw: f.raw + '\n' });
  await assert.rejects(inspectAndArchiveDesktopSession(f.root, f.rpc, changed));
  assert.deepEqual(readFileSync(join(f.root, 'session.jsonl')), original);
});

test('command rejects invalid modes and relative paths before accessing runtime', async () => {
  for (const args of [[], ['shell', '/root', '/home', '/cookie'], ['start', 'relative', '/home', '/cookie']]) {
    await assert.rejects(sessionCommand(args));
  }
});

test('verified framework reminder archives all original bytes without becoming a second prompt', async t => {
  const f = fixture(t), rows = f.reader(f.id).rows;
  const extra = [];
  for (let i = 0; i < 3; i++) extra.push(
    { type: 'tool/call', data: { callId: String(i), name: 'vm_observe', arguments: '{}' } },
    { type: 'tool/result', data: { message: { toolCallId: String(i) } } });
  extra.push({ type: 'user/message', data: { role: 'user', source: {
    kind: 'repeat-tool-reminder', form: 'notice', summary: 'vm_observe × 3' },
  content: [{ type: 'text', text: noticePolicy.gentle }] } });
  rows.splice(-1, 0, ...extra);
  const raw = rows.map((row, seq) => JSON.stringify({ ...row, seq })).join('\n') + '\n';
  writeFileSync(f.target, execFileSync('/opt/homebrew/bin/zstd', ['-q', '-c'], { input: raw }));
  const result = await inspectAndArchiveDesktopSession(f.root, f.rpc, f.reader);
  assert.equal(result.terminal, true);
  assert.equal(result.userMessages, 1);
  assert.equal(result.rawUserMessages, 2);
  assert.equal(result.frameworkNotices, 1);
  assert.equal(readFileSync(join(f.root, 'session.jsonl'), 'utf8'), raw);
});
