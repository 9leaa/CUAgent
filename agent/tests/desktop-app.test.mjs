import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, realpathSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { stopIdleDesktop, startDesktop } from '../harness/desktop-app.mjs';

function fixture(t) {
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'desktop-app-')));
  t.after(() => rmSync(base, { recursive: true }));
  const root = join(base, 'run'), home = join(base, 'home');
  for (const path of [root, home, join(home, 'profiles'), join(home, 'profiles/desktop')]) mkdirSync(path, { mode: 0o700 });
  const save = (path, data) => writeFileSync(path, JSON.stringify(data), { mode: 0o600 });
  const target = join(home, 'profiles/desktop/cordis.patch.yml');
  save(target, []);
  const hash = createHash('sha256').update('[]').digest('hex');
  save(join(root, 'profile-plan.json'), { root, home, target, beforeSha256: hash, afterSha256: hash });
  for (const phase of ['apply', 'restore']) save(join(root, `profile-${phase}-receipt.json`), { sha256: hash });
  const connection = join(root, 'c0-connection.json');
  save(connection, { runId: 'run', caseId: 'real_textedit', url: 'http://192.168.64.3:8766', token: 'x'.repeat(43) });
  const tasks = join(root, 'base-tasks.json'); save(tasks, {});
  const state = { running: true, busy: false, presets: ['p1-daily-report'], commands: [], now: 0 };
  const dependencies = {
    execute(program, args) {
      state.commands.push([program, args]);
      if (program === '/usr/bin/pgrep') {
        if (state.running) return '808\n';
        throw Object.assign(Error('not running'), { status: 1 });
      }
      if (program === '/bin/ps') return '/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness\n';
      if (program === '/bin/kill') { state.running = false; return ''; }
      if (program === '/usr/libexec/PlistBuddy') return '0.2.0-rc.2\n';
      if (program === '/usr/bin/open') {
        state.running = true;
        state.presets = args.includes('CUAGENT_C0_CONNECTION=' + connection) ? ['real-app'] : ['p1-daily-report'];
        return '';
      }
      throw Error('unexpected command');
    },
    rpc: async method => method === 'session/list' ? { items: [{ running: state.busy }] }
      : { presets: state.presets.map(id => ({ id })) },
    sleep: async ms => { state.now += ms; }, now: () => state.now,
    validateA1: () => {},
  };
  return { root, home, connection, tasks, state, dependencies };
}

test('mock App stop/start/restore preserves original preset and explicit environments', async t => {
  const f = fixture(t);
  assert.deepEqual(await stopIdleDesktop(f.root, 'unused', 'activate', f.dependencies), { stopped: true });
  assert.deepEqual(await startDesktop(f.root, f.home, 'unused', 'p6', f.connection, f.dependencies), { started: true, presets: ['real-app'] });
  await stopIdleDesktop(f.root, 'unused', 'restore', f.dependencies);
  await startDesktop(f.root, f.home, 'unused', 'restore', f.tasks, f.dependencies);
  const opens = f.state.commands.filter(([program]) => program === '/usr/bin/open');
  assert.equal(opens.length, 2);
  assert.ok(opens[0][1].includes('CUAGENT_A1_TASKS_PATH='));
  assert.ok(opens[1][1].includes('CUAGENT_C0_CONNECTION='));
});

test('busy App never receives TERM', async t => {
  const f = fixture(t); f.state.busy = true;
  await assert.rejects(stopIdleDesktop(f.root, 'unused', 'activate', f.dependencies));
  assert.ok(!f.state.commands.some(([program]) => program === '/bin/kill'));
  assert.ok(!existsSync(join(f.root, 'app-activate-stop-intent.json')));
});

test('process identity mismatch never receives TERM', async t => {
  const f = fixture(t), exec = f.dependencies.execute;
  f.dependencies.execute = (program, args) => program === '/bin/ps' ? '/other/app' : exec(program, args);
  await assert.rejects(stopIdleDesktop(f.root, 'unused', 'activate', f.dependencies));
  assert.ok(!f.state.commands.some(([program]) => program === '/bin/kill'));
});

test('TERM timeout never escalates to force kill or a second stop', async t => {
  const f = fixture(t), exec = f.dependencies.execute;
  f.dependencies.execute = (program, args) => { const result = exec(program, args); if (program === '/bin/kill') f.state.running = true; return result; };
  await assert.rejects(stopIdleDesktop(f.root, 'unused', 'activate', f.dependencies));
  await assert.rejects(stopIdleDesktop(f.root, 'unused', 'activate', f.dependencies));
  assert.equal(f.state.commands.filter(([program]) => program === '/bin/kill').length, 1);
  assert.ok(f.state.now <= 10000);
});

test('start requires stopped App and reviewed version', async t => {
  const f = fixture(t);
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p6', f.connection, f.dependencies));
  f.state.running = false;
  const exec = f.dependencies.execute;
  f.dependencies.execute = (program, args) => program === '/usr/libexec/PlistBuddy' ? 'other' : exec(program, args);
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p6', f.connection, f.dependencies));
  assert.ok(!f.state.commands.some(([program]) => program === '/usr/bin/open'));
});

test('wrong live preset after launch is not retried', async t => {
  const f = fixture(t); f.state.running = false;
  f.dependencies.rpc = async method => method === 'session/list' ? { items: [] } : { presets: [{ id: 'unexpected' }] };
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p6', f.connection, f.dependencies));
  f.state.running = false;
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p6', f.connection, f.dependencies));
  assert.equal(f.state.commands.filter(([program]) => program === '/usr/bin/open').length, 1);
});
