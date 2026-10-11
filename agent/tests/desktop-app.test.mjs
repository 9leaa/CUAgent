import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, realpathSync, rmSync, writeFileSync, existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { stopIdleDesktop, startDesktop } from '../harness/desktop-app.mjs';

function fixture(t, handoff = false) {
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'desktop-app-')));
  t.after(() => rmSync(base, { recursive: true }));
  const runId = handoff === 'calc' ? 'calc-select-11111111-1111-1111-1111-111111111111'
    : handoff ? 'p2-11111111-1111-1111-1111-111111111111' : 'run';
  const root = join(base, runId), home = join(base, 'home');
  for (const path of [root, home, join(home, 'profiles'), join(home, 'profiles/desktop')]) mkdirSync(path, { mode: 0o700 });
  const save = (path, data) => writeFileSync(path, JSON.stringify(data), { mode: 0o600 });
  const target = join(home, 'profiles/desktop/cordis.patch.yml');
  save(target, []);
  const hash = createHash('sha256').update('[]').digest('hex');
  save(join(root, 'profile-plan.json'), { root, home, target, beforeSha256: hash, afterSha256: hash });
  for (const phase of ['apply', 'restore']) save(join(root, `profile-${phase}-receipt.json`), { sha256: hash });
  const connection = join(root, 'c0-connection.json');
  save(connection, { runId, caseId: handoff ? 'project_handoff' : 'real_textedit',
    ...(handoff ? { stage: 'p7', inputSha256: 'a'.repeat(64) } : {}), url: 'http://192.168.64.3:8766', token: 'x'.repeat(43) });
  save(join(root, 'vm-tools-ready.json'), { runId,
    ...(handoff ? { kind: 'project-handoff', inputSha256: 'a'.repeat(64) } : {}),
    toolNames: handoff ? ['vm_check_draft', 'vm_locate_quote', 'vm_observe', 'vm_read_materials', 'vm_read_result', 'vm_reopen', 'vm_save', 'vm_type', 'vm_write_result']
      : ['vm_observe', 'vm_read_result', 'vm_save', 'vm_type', 'vm_write_result'] });
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
        state.presets = args.includes('CUAGENT_C0_CONNECTION=' + connection)
          ? [handoff === 'calc' ? 'calc-selection' : handoff ? 'project-handoff' : 'real-app'] : ['p1-daily-report'];
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

for (const fault of [undefined,'session','tools','protocol','extra']) {
  test(`Calc App readiness ${fault}`, async t => {
    const f = fixture(t,'calc');
    const connection = {runId:f.root.split('/').at(-1),caseId:'calc_selection',stage:'p7',
      protocol:'calc-selection-v1',sessionId:'session-22222222-2222-2222-2222-222222222222',
      cell:'A2',url:'http://192.168.64.3:8766',token:'x'.repeat(43)};
    const ready = {protocol:connection.protocol,runId:connection.runId,sessionId:connection.sessionId,
      toolNames:['vm_calc_observe','vm_calc_select','vm_calc_stop']};
    if (fault === 'session') ready.sessionId = 'other';
    if (fault === 'tools') ready.toolNames.push('shell');
    if (fault === 'protocol') connection.protocol = 'other';
    if (fault === 'extra') connection.inputMode = 'checked-draft-v1';
    writeFileSync(f.connection,JSON.stringify(connection));
    writeFileSync(join(f.root,'vm-tools-ready.json'),JSON.stringify(ready));
    f.state.running = false;
    if (fault) await assert.rejects(startDesktop(f.root,f.home,'unused','calc',f.connection,f.dependencies));
    else assert.deepEqual(await startDesktop(f.root,f.home,'unused','calc',f.connection,f.dependencies),
      {started:true,presets:['calc-selection']});
    const launches = f.state.commands.filter(([p])=>p === '/usr/bin/open');
    assert.equal(launches.length,['protocol','extra'].includes(fault) ? 0 : 1);
  });
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

test('P7 explicit launch verifies original input identity and eight tools then restores', async t => {
  const f = fixture(t, true);
  await stopIdleDesktop(f.root, 'unused', 'activate', f.dependencies);
  await startDesktop(f.root, f.home, 'unused', 'p7', f.connection, f.dependencies);
  assert.ok(existsSync(join(f.root, 'app-p7-start-receipt.json')));
  await stopIdleDesktop(f.root, 'unused', 'restore', f.dependencies);
  await startDesktop(f.root, f.home, 'unused', 'restore', f.tasks, f.dependencies);
  assert.deepEqual(f.state.presets, ['p1-daily-report']);
});

for (const fault of ['none','missing_mode','old_tools','unknown_mode','missing_protocol']) test(`P7 checked input App readiness ${fault}`, async t => {
  const f = fixture(t,true); f.state.running=false;
  const connection={...JSON.parse(readFileSync(f.connection,'utf8')),protocol:'p7-tool-submit-v1',
    sessionId:'session-22222222-2222-2222-2222-222222222222',inputMode:'checked-draft-v1'};
  const path=join(f.root,'vm-tools-ready.json');
  const ready={...JSON.parse(readFileSync(path,'utf8')),protocol:connection.protocol,sessionId:connection.sessionId,inputMode:connection.inputMode};
  ready.toolNames=[...ready.toolNames.map(n=>n==='vm_type'?'vm_type_checked_draft':n),'vm_submit_handoff'].sort();
  if (fault==='missing_mode') delete ready.inputMode;
  if (fault==='old_tools') ready.toolNames=ready.toolNames.map(n=>n==='vm_type_checked_draft'?'vm_type':n);
  if (fault==='unknown_mode') connection.inputMode='auto';
  if (fault==='missing_protocol') delete connection.protocol;
  writeFileSync(f.connection,JSON.stringify(connection)); writeFileSync(path,JSON.stringify(ready));
  if (fault==='none') {
    await startDesktop(f.root,f.home,'unused','p7',f.connection,f.dependencies);
    assert.ok(existsSync(join(f.root,'app-p7-start-receipt.json')));
  } else {
    await assert.rejects(startDesktop(f.root,f.home,'unused','p7',f.connection,f.dependencies));
    assert.ok(!existsSync(join(f.root,'app-p7-start-receipt.json')));
    if (['unknown_mode','missing_protocol'].includes(fault)) assert.ok(!f.state.commands.some(([p])=>p==='/usr/bin/open'));
  }
});

for (const fault of ['none', 'wrong_session', 'legacy_tools', 'unknown_protocol']) test(`P7 new protocol App readiness ${fault}`, async t => {
  const f = fixture(t, true); f.state.running = false;
  const protocol = 'p7-tool-submit-v1', sessionId = 'session-22222222-2222-2222-2222-222222222222';
  const connection = {...JSON.parse(readFileSync(f.connection, 'utf8')), protocol, sessionId};
  const path = join(f.root, 'vm-tools-ready.json');
  const ready = {...JSON.parse(readFileSync(path, 'utf8')), protocol, sessionId};
  if (fault !== 'legacy_tools') ready.toolNames = [...ready.toolNames, 'vm_submit_handoff'].sort();
  if (fault === 'wrong_session') ready.sessionId = 'session-33333333-3333-3333-3333-333333333333';
  if (fault === 'unknown_protocol') connection.protocol = 'unknown';
  writeFileSync(f.connection, JSON.stringify(connection)); writeFileSync(path, JSON.stringify(ready));
  if (fault === 'none') {
    await startDesktop(f.root, f.home, 'unused', 'p7', f.connection, f.dependencies);
    assert.ok(existsSync(join(f.root, 'app-p7-start-receipt.json')));
  } else {
    await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p7', f.connection, f.dependencies));
    assert.ok(!existsSync(join(f.root, 'app-p7-start-receipt.json')));
    if (fault === 'unknown_protocol') assert.ok(!f.state.commands.some(([p]) => p === '/usr/bin/open'));
  }
});

test('P6 cannot launch P7 connection and P7 cannot accept mismatched ready receipt', async t => {
  const f = fixture(t, true); f.state.running = false;
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p6', f.connection, f.dependencies));
  assert.ok(!f.state.commands.some(([program]) => program === '/usr/bin/open'));
  writeFileSync(join(f.root, 'vm-tools-ready.json'), JSON.stringify({ runId: 'wrong', toolNames: [] }), { mode: 0o600 });
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p7', f.connection, f.dependencies));
  assert.ok(!existsSync(join(f.root, 'app-p7-start-receipt.json')));
  f.state.running = false;
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p7', f.connection, f.dependencies));
  assert.equal(f.state.commands.filter(([program]) => program === '/usr/bin/open').length, 1);
});

test('busy App never receives TERM', async t => {
  const f = fixture(t); f.state.busy = true;
  await assert.rejects(stopIdleDesktop(f.root, 'unused', 'activate', f.dependencies));
  assert.ok(!f.state.commands.some(([program]) => program === '/bin/kill'));
  assert.ok(!existsSync(join(f.root, 'app-activate-stop-intent.json')));
});

test('preset alone does not prove tools loaded', async t => {
  const f = fixture(t); f.state.running = false;
  rmSync(join(f.root, 'vm-tools-ready.json'));
  await assert.rejects(startDesktop(f.root, f.home, 'unused', 'p6', f.connection, f.dependencies));
  assert.ok(!existsSync(join(f.root, 'app-p6-start-receipt.json')));
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
