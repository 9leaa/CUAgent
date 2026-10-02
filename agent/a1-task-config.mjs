/** Shared read-only approval validation for launch preflight and runtime. */
import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, realpathSync } from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, sep } from 'node:path';
import { A1Policy } from './a1-policy.mjs';

const inside = (root, target) => {
  const path = relative(root, target);
  return path === '' || (!isAbsolute(path) && path !== '..' && !path.startsWith(`..${sep}`));
};

export function loadA1TaskConfig(configured) {
  if (typeof configured !== 'string' || !isAbsolute(configured)) throw new Error('absolute A1 task config required');
  if (lstatSync(configured).isSymbolicLink()) throw new Error('private A1 task config required');
  const path = realpathSync(configured), stat = lstatSync(path);
  if (!stat.isFile() || stat.size > 65536 || (stat.mode & 0o077) !== 0) throw new Error('private A1 task config required');
  const text = readFileSync(path, 'utf8'), config = JSON.parse(text);
  if (config.version !== 1 || !Array.isArray(config.tasks) || config.tasks.length < 1 || config.tasks.length > 20) throw new Error('invalid A1 task config');
  const policies = new Map(), roots = [], runs = new Set(), ledgers = new Set();
  for (const task of config.tasks) {
    if (!task || typeof task !== 'object') throw new Error('invalid A1 task');
    if (policies.has(task.sessionId) || runs.has(task.runId)) throw new Error('duplicate A1 task identity');
    const root = realpathSync(task.workspaceRoot);
    if (inside(root, path) || roots.some(other => inside(other, root) || inside(root, other))) throw new Error('overlapping A1 task scope');
    roots.push(root); runs.add(task.runId);
    const policy = new A1Policy(task);
    const ledger = join(realpathSync(dirname(task.ledgerPath)), basename(task.ledgerPath));
    if (ledgers.has(ledger)) throw new Error('duplicate A1 audit ledger');
    ledgers.add(ledger); policies.set(task.sessionId, policy);
  }
  for (const ledger of ledgers) if (roots.some(root => inside(root, ledger))) throw new Error('audit inside another A1 workspace');
  return { path, digest: createHash('sha256').update(text).digest('hex'), policies };
}
