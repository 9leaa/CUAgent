import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, realpathSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { mergeDesktopPatch, stageProfile, applyDesktopProfile, restoreDesktopProfile, prepareDesktopProfile } from '../harness/desktop-profile.mjs';

const sha = data => createHash('sha256').update(data).digest('hex');
function fixture(t) {
  const temp = realpathSync(mkdtempSync(join(tmpdir(), 'desktop-profile-')));
  t.after(() => rmSync(temp, { recursive: true }));
  const root = join(temp, 'run'), home = join(temp, 'home');
  for (const path of [root, home, join(home, 'profiles'), join(home, 'profiles/desktop'), join(root, 'desktop-plugins')]) mkdirSync(path, { mode: 0o700 });
  const target = join(home, 'profiles/desktop/cordis.patch.yml');
  const before = '# preserve exact bytes\n- id: account\n  config: {}\n';
  writeFileSync(target, before, { mode: 0o600 });
  const plugins = {};
  for (const name of ['c0-vm-tools.mjs', 'desktop-tool-scope.mjs']) {
    writeFileSync(join(root, 'desktop-plugins', name), '// test plugin\n', { mode: 0o600 });
    plugins[name] = sha('// test plugin\n');
  }
  return { root, home, target, before, plugins };
}

test('merge changes only reviewed IDs and retains unrelated account config', () => {
  const account = { id: 'account', config: { reference: 'private-account' } };
  const before = [account, { insert: [{ id: 'preset-p1-daily-report' }, { id: 'unrelated' }] }, { id: 'desktop-tool-scope' }];
  const additions = [{ insert: [{ id: 'preset-real-app' }, { id: 'desktop-tool-scope' }] }];
  assert.deepEqual(mergeDesktopPatch(before, additions), [account, { insert: [{ id: 'unrelated' }] }, ...additions]);
  assert.equal(before[1].insert.length, 2);
});

test('P7 and P6 preset switching removes the other reviewed preset only', () => {
  const account = { id: 'account', config: { keep: true } };
  const p7 = [{ insert: [{ id: 'preset-project-handoff' }] }];
  const p6 = [{ insert: [{ id: 'preset-real-app' }] }];
  assert.deepEqual(mergeDesktopPatch([account, ...p6], p7), [account, ...p7]);
  assert.deepEqual(mergeDesktopPatch([account, ...p7], p6), [account, ...p6]);
});

test('P7 fixed compiler preparation creates only staged profile and keeps active bytes',
  { skip: !process.env.CUAGENT_TEST_BUILD_TOOLS }, async t => {
    const f = fixture(t);
    rmSync(join(f.root, 'desktop-plugins'), { recursive: true });
    await prepareDesktopProfile(f.root, f.home, process.env.CUAGENT_TEST_BUILD_TOOLS, 'project-handoff');
    const candidate = readFileSync(join(f.root, 'profile-next.yml'), 'utf8');
    assert.match(candidate, /default: project-handoff/u);
    assert.match(candidate, /preset-project-handoff/u);
    assert.match(candidate, /vm_reopen/u);
    assert.doesNotMatch(candidate, /preset-real-app/u);
    assert.equal(readFileSync(f.target, 'utf8'), f.before);
});

test('prepare does not mutate home; apply then restore returns exact original bytes', t => {
  const f = fixture(t);
  stageProfile(f.root, f.home, '[]\n', f.plugins);
  assert.equal(readFileSync(f.target, 'utf8'), f.before);
  let checks = 0;
  const stopped = () => { checks++; };
  assert.deepEqual(applyDesktopProfile(f.root, f.home, stopped), { applied: true });
  assert.equal(readFileSync(f.target, 'utf8'), '[]\n');
  assert.deepEqual(restoreDesktopProfile(f.root, f.home, stopped), { restored: true });
  assert.equal(readFileSync(f.target, 'utf8'), f.before);
  assert.equal(checks, 4);
  assert.ok(!existsSync(join(f.home, 'profiles/desktop/.cuagent-profile.lock')));
});

test('running App blocks change before intent or profile write', t => {
  const f = fixture(t);
  stageProfile(f.root, f.home, '[]\n', f.plugins);
  assert.throws(() => applyDesktopProfile(f.root, f.home, () => { throw Error('App running'); }));
  assert.equal(readFileSync(f.target, 'utf8'), f.before);
  assert.ok(!existsSync(join(f.root, 'profile-apply-intent.json')));
});

test('reviewed parser allows formatting only and preserves observed bytes', t => {
  const f = fixture(t);
  stageProfile(f.root, f.home, '[{"value":"off"}]', f.plugins);
  applyDesktopProfile(f.root, f.home, () => {});
  const formatted = '[ { "value": "off" } ]\n';
  writeFileSync(f.target, formatted);
  restoreDesktopProfile(f.root, f.home, () => {}, JSON.parse);
  assert.equal(readFileSync(f.target, 'utf8'), f.before);
  assert.equal(readFileSync(join(f.root, 'profile-restore-observed.yml'), 'utf8'), formatted);
});

test('reviewed parser still rejects semantic changes', t => {
  const f = fixture(t);
  stageProfile(f.root, f.home, '[{"value":"off"}]', f.plugins);
  applyDesktopProfile(f.root, f.home, () => {});
  writeFileSync(f.target, '[{"value":"high"}]');
  assert.throws(() => restoreDesktopProfile(f.root, f.home, () => {}, JSON.parse));
  assert.ok(!existsSync(join(f.root, 'profile-restore-intent.json')));
});

test('outside edits prevent apply and prevent restore overwrite', t => {
  const f = fixture(t);
  stageProfile(f.root, f.home, '[]\n', f.plugins);
  writeFileSync(f.target, 'external');
  assert.throws(() => applyDesktopProfile(f.root, f.home, () => {}));
  writeFileSync(f.target, f.before);
  applyDesktopProfile(f.root, f.home, () => {});
  writeFileSync(f.target, 'external');
  assert.throws(() => restoreDesktopProfile(f.root, f.home, () => {}));
  assert.equal(readFileSync(f.target, 'utf8'), 'external');
});

test('changed plugins and prior operation lock prevent switching', t => {
  const f = fixture(t);
  stageProfile(f.root, f.home, '[]\n', f.plugins);
  writeFileSync(join(f.root, 'desktop-plugins/c0-vm-tools.mjs'), 'tampered');
  assert.throws(() => applyDesktopProfile(f.root, f.home, () => {}));
  writeFileSync(join(f.home, 'profiles/desktop/.cuagent-profile.lock'), 'occupied', { mode: 0o600 });
  assert.throws(() => applyDesktopProfile(f.root, f.home, () => {}));
  assert.equal(readFileSync(f.target, 'utf8'), f.before);
});

test('preparation refuses an input that changed while rendering', t => {
  const f = fixture(t);
  assert.throws(() => stageProfile(f.root, f.home, '[]', f.plugins, Buffer.from('previous version')));
  assert.ok(!existsSync(join(f.root, 'profile-before.yml')));
});

test('restoration cannot target a different home', t => {
  const f = fixture(t), other = fixture(t);
  stageProfile(f.root, f.home, '[]', f.plugins);
  assert.throws(() => restoreDesktopProfile(f.root, other.home, () => {}));
  assert.equal(readFileSync(other.target, 'utf8'), other.before);
});

test('optional real pinned compiler builds into temporary run without altering profile',
  { skip: !process.env.CUAGENT_TEST_BUILD_TOOLS }, async t => {
    const f = fixture(t);
    rmSync(join(f.root, 'desktop-plugins'), { recursive: true }); // Only fixture-owned synthetic plugins.
    const result = await prepareDesktopProfile(f.root, f.home, process.env.CUAGENT_TEST_BUILD_TOOLS);
    assert.equal(result.prepared, true);
    assert.equal(readFileSync(f.target, 'utf8'), f.before);
    assert.match(readFileSync(join(f.root, 'profile-next.yml'), 'utf8'), /preset-real-app/u);
    assert.match(readFileSync(join(f.root, 'profile-next.yml'), 'utf8'), /id: account/u);
    assert.ok(readFileSync(join(f.root, 'desktop-plugins/c0-vm-tools.mjs')).length > 1000);
    const plan = JSON.parse(readFileSync(join(f.root, 'profile-plan.json')));
    assert.ok(plan.installedPlugins.startsWith(join(f.home, 'profiles/desktop') + '/'));
    assert.match(readFileSync(f.target, 'utf8'), /account/);
    for (const [name, digest] of Object.entries(plan.plugins)) {
      assert.equal(sha(readFileSync(join(plan.installedPlugins, name))), digest);
    }
    applyDesktopProfile(f.root, f.home, () => {});
    restoreDesktopProfile(f.root, f.home, () => {});
    assert.equal(readFileSync(f.target, 'utf8'), f.before);
  });
