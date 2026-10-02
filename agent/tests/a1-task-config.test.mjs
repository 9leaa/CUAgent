import assert from 'node:assert/strict';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { loadA1TaskConfig } from '../a1-task-config.mjs';

function fixture(t) {
  const dir = mkdtempSync(join(tmpdir(), 'a1-config-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const tasks = ['one', 'two'].map(id => {
    const workspaceRoot = join(dir, id), audit = join(dir, `audit-${id}`);
    mkdirSync(workspaceRoot); mkdirSync(audit, { mode: 0o700 });
    return { workspaceRoot, ledgerPath: join(audit, 'calls.jsonl'), runId: id, sessionId: `session-${id}`, allowedTools: ['workspace_read'] };
  });
  const path = join(dir, 'tasks.json');
  const save = (value = tasks) => writeFileSync(path, JSON.stringify({ version: 1, tasks: value }), { mode: 0o600 });
  save(); return { dir, tasks, path, save };
}

test('shared approval validation reads two tasks without creating or changing ledgers/config', t => {
  const { path, tasks } = fixture(t), before = readFileSync(path);
  const loaded = loadA1TaskConfig(path);
  assert.equal(loaded.policies.size, 2);
  assert.equal(loaded.policies.get('session-one').count(), 0);
  assert.deepEqual(readFileSync(path), before);
  for (const task of tasks) assert.equal(existsSync(task.ledgerPath), false);
});
test('shared approval validation rejects missing, symlinked and non-private config', t => {
  const { dir, path } = fixture(t);
  assert.throws(() => loadA1TaskConfig(join(dir, 'missing.json')));
  const alias = join(dir, 'alias.json'); symlinkSync(path, alias);
  assert.throws(() => loadA1TaskConfig(alias), /private/);
  chmodSync(path, 0o644); assert.throws(() => loadA1TaskConfig(path), /private/);
});
test('shared approval validation rejects duplicate session, run and canonical ledger aliases', t => {
  const { dir, path, tasks, save } = fixture(t);
  for (const field of ['sessionId', 'runId', 'ledgerPath']) {
    save([tasks[0], { ...tasks[1], [field]: tasks[0][field] }]);
    assert.throws(() => loadA1TaskConfig(path), /duplicate/);
  }
  const alias = join(dir, 'audit-alias'); symlinkSync(join(dir, 'audit-one'), alias);
  save([tasks[0], { ...tasks[1], ledgerPath: join(alias, 'calls.jsonl') }]);
  assert.throws(() => loadA1TaskConfig(path), /duplicate/);
});
test('shared approval validation rejects nested and symlink-aliased model roots', t => {
  const { dir, path, tasks, save } = fixture(t);
  const nested = join(tasks[0].workspaceRoot, 'nested'); mkdirSync(nested);
  save([tasks[0], { ...tasks[1], workspaceRoot: nested }]);
  assert.throws(() => loadA1TaskConfig(path), /overlapping/);
  const alias = join(dir, 'root-alias'); symlinkSync(tasks[0].workspaceRoot, alias);
  save([tasks[0], { ...tasks[1], workspaceRoot: alias }]);
  assert.throws(() => loadA1TaskConfig(path), /overlapping/);
});
test('shared approval validation rejects config or another task audit within any model root', t => {
  const { path, tasks, save } = fixture(t);
  const exposed = join(tasks[0].workspaceRoot, 'config.json');
  writeFileSync(exposed, readFileSync(path), { mode: 0o600 });
  assert.throws(() => loadA1TaskConfig(exposed), /overlapping/);
  const audit = join(tasks[0].workspaceRoot, 'audit-two'); mkdirSync(audit, { mode: 0o700 });
  save([tasks[0], { ...tasks[1], ledgerPath: join(audit, 'calls.jsonl') }]);
  assert.throws(() => loadA1TaskConfig(path), /another A1 workspace/);
});
