/** Official App lifecycle only. Caller must own desktop lock and cutover window. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { closeSync, constants, fsyncSync, lstatSync, openSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { isAbsolute, join, resolve } from 'node:path';
import { createDesktopRpc } from './desktop-session.mjs';
import { loadA1TaskConfig } from '../a1-task-config.mjs';
import { handoffTools } from './handoff-prompt.mjs';

const APP = '/Applications/DeepSeek Harness.app';
const EXECUTABLE = APP + '/Contents/MacOS/DeepSeek Harness';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const execute = (program, args) => execFileSync(program, args, { encoding: 'utf8', timeout: 5000, stdio: ['ignore', 'pipe', 'ignore'] });
function privatePath(path, directory = false) {
  assert.ok(isAbsolute(path) && resolve(path) === path && realpathSync(path) === path);
  const stat = lstatSync(path);
  assert.ok((directory ? stat.isDirectory() : stat.isFile()) && stat.uid === process.getuid() && !(stat.mode & 0o077));
  if (!directory) assert.ok(stat.size <= 1024 * 1024);
  return path;
}
const load = path => JSON.parse(readFileSync(privatePath(path), 'utf8'));
function save(root, name, value) {
  const fd = openSync(join(root, name), constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
  try { writeFileSync(fd, JSON.stringify(value)); fsyncSync(fd); } finally { closeSync(fd); }
}
function pids(exec) {
  try {
    const output = exec('/usr/bin/pgrep', ['-f', '^' + EXECUTABLE + '$']).trim();
    assert.match(output, /^[0-9]+(?:\n[0-9]+)*$/u);
    const values = output.split('\n');
    assert.ok(values.every(value => Number(value) > 1));
    return values;
  } catch (error) {
    if (error.status === 1) return [];
    throw error;
  }
}
async function idle(rpc) {
  const result = await rpc('session/list', { _request: {} });
  assert.ok(Array.isArray(result.items) && result.items.every(item => item.running === false));
}

export async function stopIdleDesktop(root, cookie, phase, dependencies = {}) {
  privatePath(root, true);
  assert.ok(['activate', 'restore'].includes(phase));
  const exec = dependencies.execute ?? execute, wait = dependencies.sleep ?? sleep;
  const rpc = dependencies.rpc ?? createDesktopRpc(cookie);
  await idle(rpc);
  const presets = (await rpc('agentPresets/list', {})).presets.map(preset => preset.id).sort();
  assert.ok(presets.length > 0 && presets.every(id => typeof id === 'string'));
  const processes = pids(exec);
  assert.equal(processes.length, 1);
  const pid = processes[0];
  assert.equal(exec('/bin/ps', ['-p', pid, '-o', 'command=']).trim(), EXECUTABLE);
  await idle(rpc); // Recheck immediately before the irreversible stop request.
  save(root, `app-${phase}-stop-intent.json`, { pid, presets });
  exec('/bin/kill', ['-TERM', pid]);
  const now = dependencies.now ?? Date.now, deadline = now() + 10000;
  for (let attempt = 0; attempt < 100 && now() < deadline; attempt++) {
    if (!pids(exec).includes(pid)) {
      assert.ok(now() <= deadline);
      save(root, `app-${phase}-stop-receipt.json`, { pid, exited: true });
      return { stopped: true };
    }
    await wait(100);
  }
  throw Error('DESKTOP_APP_STOP_UNCONFIRMED');
}

export async function startDesktop(root, home, cookie, mode, launchFile, dependencies = {}) {
  privatePath(root, true); privatePath(home, true);
  assert.ok(['p6', 'p7', 'restore'].includes(mode));
  const taskMode = mode !== 'restore';
  const exec = dependencies.execute ?? execute, wait = dependencies.sleep ?? sleep;
  const rpc = dependencies.rpc ?? createDesktopRpc(cookie);
  assert.equal(pids(exec).length, 0);
  assert.equal(exec('/usr/libexec/PlistBuddy', ['-c', 'Print :CFBundleShortVersionString', APP + '/Contents/Info.plist']).trim(), '0.2.0-rc.2');
  const plan = load(join(root, 'profile-plan.json'));
  assert.equal(plan.root, root); assert.equal(plan.home, home);
  assert.equal(plan.target, join(home, 'profiles/desktop/cordis.patch.yml'));
  const hash = taskMode ? plan.afterSha256 : plan.beforeSha256;
  assert.equal(load(join(root, `profile-${taskMode ? 'apply' : 'restore'}-receipt.json`)).sha256, hash);
  assert.equal(sha(readFileSync(privatePath(plan.target))), hash);
  let environment, expected, handoffBinding;
  if (taskMode) {
    assert.equal(launchFile, join(root, 'c0-connection.json'));
    const connection = load(launchFile);
    assert.equal(connection.runId, root.split('/').at(-1));
    assert.equal(connection.caseId, mode === 'p7' ? 'project_handoff' : 'real_textedit');
    if (mode === 'p7') {
      assert.equal(connection.stage, 'p7');
      assert.match(connection.runId, /^p2-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/u);
      assert.match(connection.inputSha256, /^[0-9a-f]{64}$/u);
      const submit = Object.hasOwn(connection, 'protocol');
      if (submit) {
        assert.equal(connection.protocol, 'p7-tool-submit-v1');
        assert.match(connection.sessionId, /^session-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/u);
      }
      handoffBinding = { runId: connection.runId, kind: 'project-handoff', inputSha256: connection.inputSha256,
        toolNames: handoffTools(connection.protocol),
        ...(submit ? { protocol: connection.protocol, sessionId: connection.sessionId } : {}) };
    }
    assert.equal(connection.url, 'http://192.168.64.3:8766');
    assert.match(connection.token, /^[A-Za-z0-9_-]{43,60}$/u);
    environment = [`DSH_HOME=${home}`, `CUAGENT_C0_CONNECTION=${launchFile}`,
      `CUAGENT_C0_AUDIT_PATH=${join(root, 'request-audit.jsonl')}`, 'CUAGENT_A1_TASKS_PATH='];
    expected = [mode === 'p7' ? 'project-handoff' : 'real-app'];
  } else {
    privatePath(launchFile);
    (dependencies.validateA1 ?? loadA1TaskConfig)(launchFile);
    environment = [`DSH_HOME=${home}`, `CUAGENT_A1_TASKS_PATH=${launchFile}`, 'CUAGENT_C0_CONNECTION=', 'CUAGENT_C0_AUDIT_PATH='];
    expected = load(join(root, 'app-activate-stop-intent.json')).presets;
    assert.ok(Array.isArray(expected) && expected.length > 0);
  }
  save(root, `app-${mode}-start-intent.json`, { home, launchFile, expectedPresets: expected });
  exec('/usr/bin/open', [...environment.flatMap(value => ['--env', value]), '-a', APP]);
  const now = dependencies.now ?? Date.now;
  const deadline = now() + 45000;
  while (now() < deadline) {
    let presets;
    try {
      await idle(rpc);
      presets = (await rpc('agentPresets/list', {})).presets.map(preset => preset.id).sort();
    } catch (error) {
      if (error.message !== 'DESKTOP_RPC_UNCONFIRMED') throw error;
      await wait(250);
      continue;
    }
    assert.deepEqual(presets, expected);
    if (taskMode) {
      const ready = load(join(root, 'vm-tools-ready.json'));
      assert.equal(ready.runId, root.split('/').at(-1));
      if (mode === 'p7') assert.deepEqual(ready, handoffBinding);
      else assert.deepEqual(ready.toolNames, ['vm_observe', 'vm_read_result', 'vm_save', 'vm_type', 'vm_write_result']);
    }
    assert.equal(pids(exec).length, 1);
    assert.equal(sha(readFileSync(privatePath(plan.target))), hash);
    save(root, `app-${mode}-start-receipt.json`, { home, presets, profileSha256: hash });
    return { started: true, presets };
  }
  throw Error('DESKTOP_APP_START_UNCONFIRMED');
}
