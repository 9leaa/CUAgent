/** Explicit profile transaction. Never starts/stops the App or copies credentials. */
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { closeSync, constants, fsyncSync, lstatSync, mkdirSync, openSync, readFileSync,
  realpathSync, renameSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const project = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const controlled = new Set(['preset-p1-daily-report', 'preset-p4-report-inputs', 'cuagent-a0-policy',
  'preset-a0-verify', 'cuagent-desktop-request-audit', 'preset-c0-calculator', 'preset-c0-ui',
  'preset-c1-controlled', 'preset-c2-controlled', 'preset-real-app', 'c0-vm-tools',
  'cuagent-a1-policy', 'preset-a1-controlled', 'preset-a1-readonly', 'cuagent-a1-request-audit', 'desktop-tool-scope', 'preset-project-handoff', 'preset-calc-selection']);

function privatePath(path, directory) {
  assert.ok(isAbsolute(path) && resolve(path) === path && realpathSync(path) === path);
  const info = lstatSync(path);
  assert.ok((directory ? info.isDirectory() : info.isFile()) && info.uid === process.getuid() && !(info.mode & 0o077));
  if (!directory) assert.ok(info.size <= 1024 * 1024);
  return path;
}
function save(path, bytes) {
  const fd = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
  try { writeFileSync(fd, bytes); fsyncSync(fd); } finally { closeSync(fd); }
}
function location(root, home) {
  privatePath(root, true); privatePath(home, true);
  const profile = privatePath(join(home, 'profiles', 'desktop'), true);
  return privatePath(join(profile, 'cordis.patch.yml'), false);
}
function appStopped() {
  const result = spawnSync('/usr/bin/pgrep', ['-f', '^/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness$'], { stdio: 'ignore' });
  assert.equal(result.status, 1, 'App must already be stopped; unknown process state is not idle');
}

export function mergeDesktopPatch(before, additions) {
  assert.ok(Array.isArray(before) && Array.isArray(additions));
  const ids = new Set([...controlled, ...additions.flatMap(row => row.insert?.map(child => child.id) ?? [row.id])]);
  const retained = before.flatMap(row => {
    assert.ok(row && typeof row === 'object');
    if (row.insert) {
      const insert = row.insert.filter(child => !ids.has(child.id));
      return insert.length ? [{ ...row, insert }] : [];
    }
    return ids.has(row.id) ? [] : [row];
  });
  return [...retained, ...additions];
}

export function stageProfile(root, home, candidate, plugins, expectedBefore, installedPlugins) {
  const target = location(root, home);
  assert.ok(typeof candidate === 'string' && Buffer.byteLength(candidate) <= 1024 * 1024);
  assert.deepEqual(Object.keys(plugins).sort(), ['c0-vm-tools.mjs', 'desktop-tool-scope.mjs']);
  const before = readFileSync(target);
  if (expectedBefore !== undefined) assert.deepEqual(before, expectedBefore, 'profile changed during preparation');
  const plan = { version: 1, root, home, target, beforeSha256: sha(before), afterSha256: sha(candidate), plugins,
    ...(installedPlugins ? { installedPlugins } : {}) };
  save(join(root, 'profile-before.yml'), before);
  save(join(root, 'profile-next.yml'), candidate);
  save(join(root, 'profile-plan.json'), JSON.stringify(plan));
  return { prepared: true, beforeSha256: plan.beforeSha256, afterSha256: plan.afterSha256 };
}

export async function prepareDesktopProfile(root, home, buildTools, kind = 'desktop-textedit') {
  assert.ok(['desktop-textedit', 'project-handoff', 'calc-selection'].includes(kind));
  location(root, home);
  // Shared compiler dependencies contain no task credentials; read-only use of
  // an owned 0755 installation is allowed, unlike private home/run evidence.
  assert.ok(isAbsolute(buildTools) && realpathSync(buildTools) === buildTools);
  const toolsInfo = lstatSync(buildTools);
  assert.ok(toolsInfo.isDirectory() && toolsInfo.uid === process.getuid() && !(toolsInfo.mode & 0o022));
  const { load, dump } = await import(pathToFileURL(join(buildTools, 'node_modules/js-yaml/index.js')).href);
  const { build, version } = await import(pathToFileURL(join(buildTools, 'node_modules/esbuild/lib/main.js')).href);
  assert.equal(version, '0.28.1');
  const output = join(root, 'desktop-plugins');
  mkdirSync(output, { mode: 0o700 });
  await build({ entryPoints: ['c0-vm-tools', 'desktop-tool-scope'].map(name => join(project, 'agent/harness', name + '.ts')),
    outdir: output, outExtension: { '.js': '.mjs' }, bundle: true, platform: 'node', format: 'esm',
    target: 'node24', external: ['@deepseek-ai/*'], sourcemap: false, write: false }).then(result => {
    assert.equal(result.outputFiles.length, 2);
    for (const file of result.outputFiles) {
      assert.ok([join(output, 'c0-vm-tools.mjs'), join(output, 'desktop-tool-scope.mjs')].includes(file.path));
      save(file.path, file.contents);
    }
  });
  const template = readFileSync(join(project, 'agent/harness', kind === 'calc-selection'
    ? 'cordis.desktop.calc.patch.yml' : kind === 'project-handoff'
      ? 'cordis.desktop.handoff.patch.yml' : 'cordis.desktop.real-app.patch.yml'), 'utf8');
  const installedPlugins = join(home, 'profiles/desktop', 'cuagent-p6-' + randomUUID());
  mkdirSync(installedPlugins, { mode: 0o700 });
  for (const name of ['c0-vm-tools.mjs', 'desktop-tool-scope.mjs']) save(join(installedPlugins, name), readFileSync(join(output, name)));
  const additions = load(template.replaceAll('@@PLUGIN_URL@@', pathToFileURL(installedPlugins).href));
  const original = readFileSync(location(root, home));
  const candidate = dump(mergeDesktopPatch(load(original.toString('utf8')) ?? [], additions), { lineWidth: 110 });
  const plugins = Object.fromEntries(['c0-vm-tools.mjs', 'desktop-tool-scope.mjs'].map(name => [name, sha(readFileSync(join(output, name)))]));
  return stageProfile(root, home, candidate, plugins, original, installedPlugins);
}

function changeProfile(root, home, restore, assertStopped, parseYaml) {
  const target = location(root, home);
  const plan = JSON.parse(readFileSync(privatePath(join(root, 'profile-plan.json'), false), 'utf8'));
  assert.equal(plan.version, 1); assert.equal(plan.root, root); assert.equal(plan.home, home); assert.equal(plan.target, target);
  assertStopped();
  const lock = join(dirname(target), '.cuagent-profile.lock');
  const lockFd = openSync(lock, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
  let temporary;
  try {
    const before = readFileSync(privatePath(join(root, 'profile-before.yml'), false));
    const next = readFileSync(privatePath(join(root, 'profile-next.yml'), false));
    assert.equal(sha(before), plan.beforeSha256); assert.equal(sha(next), plan.afterSha256);
    const observed = readFileSync(target), observedSha = sha(observed);
    if (restore && observedSha !== plan.afterSha256 && parseYaml) {
      assert.deepEqual(parseYaml(observed.toString()), parseYaml(next.toString()), 'profile changed semantically');
      save(join(root, 'profile-restore-observed.yml'), observed);
    } else assert.equal(observedSha, restore ? plan.afterSha256 : plan.beforeSha256, 'profile changed externally');
    if (!restore) {
      assert.deepEqual(Object.keys(plan.plugins).sort(), ['c0-vm-tools.mjs', 'desktop-tool-scope.mjs']);
      for (const [name, digest] of Object.entries(plan.plugins)) assert.equal(sha(readFileSync(privatePath(join(root, 'desktop-plugins', name), false))), digest);
      if (plan.installedPlugins) {
        assert.equal(dirname(plan.installedPlugins), dirname(target));
        privatePath(plan.installedPlugins, true);
        for (const [name, digest] of Object.entries(plan.plugins)) assert.equal(sha(readFileSync(privatePath(join(plan.installedPlugins, name), false))), digest);
      }
    }
    const prefix = restore ? 'profile-restore' : 'profile-apply';
    save(join(root, prefix + '-intent.json'), JSON.stringify({ target, beforeSha256: sha(readFileSync(target)) }));
    assertStopped();
    temporary = join(dirname(target), '.cuagent-' + randomUUID() + '.tmp');
    save(temporary, restore ? before : next);
    assert.equal(sha(readFileSync(privatePath(target, false))), observedSha);
    renameSync(temporary, target); temporary = undefined;
    save(join(root, prefix + '-receipt.json'), JSON.stringify({ sha256: sha(readFileSync(target)) }));
    return { [restore ? 'restored' : 'applied']: true };
  } finally {
    if (temporary) unlinkSync(temporary);
    closeSync(lockFd); unlinkSync(lock);
  }
}
export const applyDesktopProfile = (root, home, assertStopped = appStopped) => changeProfile(root, home, false, assertStopped);
export const restoreDesktopProfile = (root, home, assertStopped = appStopped, parseYaml) => changeProfile(root, home, true, assertStopped, parseYaml);
