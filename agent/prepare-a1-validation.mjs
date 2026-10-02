/** Prepare new task directories and protected approval/oracle metadata; never overwrite. */
import { createHash, randomUUID } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { A1_TEXT_INPUTS, expectedTextRecords } from './a1-text-verifier.mjs';
import { A1_SALES_SOURCE, A1_SALES_EXPECTED } from './a1-csv-verifier.mjs';
import { A1_REVIEWED_TOOLS } from './a1-policy.mjs';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const batch = process.argv[2];
if (process.argv.length !== 3 || !/^[A-Za-z0-9_-]{1,60}$/.test(batch ?? '')) throw new Error('usage: prepare-a1-validation.mjs <new-batch-id>');
const dir = join(root, '.runtime', 'runs', batch);
mkdirSync(dir, { mode: 0o700 });
const save = (path, value) => writeFileSync(path, JSON.stringify(value, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
const tasks = [];
for (const kind of ['texts', 'csv']) {
	const taskDir = join(dir, kind); mkdirSync(taskDir, { mode: 0o700 });
	const workspaceRoot = join(taskDir, 'workspace'); mkdirSync(workspaceRoot, { mode: 0o700 });
	const audit = join(taskDir, 'audit'); mkdirSync(audit, { mode: 0o700 });
	const inputs = kind === 'texts' ? A1_TEXT_INPUTS : { 'sales.csv': A1_SALES_SOURCE };
	for (const [path, content] of Object.entries(inputs)) writeFileSync(join(workspaceRoot, path), content, { mode: 0o600, flag: 'wx' });
	save(join(taskDir, 'expected.json'), kind === 'texts' ? { records: expectedTextRecords() } : A1_SALES_EXPECTED);
	const task = { runId: `${batch}_${kind}`, sessionId: `session-${randomUUID()}`, workspaceRoot, ledgerPath: join(audit, 'calls.jsonl'), allowedTools: [...A1_REVIEWED_TOOLS] };
	tasks.push(task);
	save(join(taskDir, 'task.json'), { kind, ...task });
}
save(join(dir, 'tasks.json'), { version: 1, tasks });
const files = ['agent/a1-policy.mjs', 'agent/a1-text-verifier.mjs', 'agent/a1-csv-verifier.mjs', 'agent/workspace-csv-stats.mjs', 'agent/harness/a1-policy-plugin.ts', 'agent/harness/a1-tools.ts', 'agent/harness/a1-request-audit.ts', 'agent/harness/cordis.desktop.a1.patch.yml'];
save(join(dir, 'metadata.json'), { batch, createdAt: new Date().toISOString(), stage: 'A1', status: 'UNVERIFIED', expectedApp: '0.2.0-rc.2', expectedModel: 'deepseek-account/deepseek-flash', hashes: Object.fromEntries(files.map(path => [path, createHash('sha256').update(readFileSync(join(root, path))).digest('hex')])) });
console.log(JSON.stringify({ prepared: true, batch, taskConfig: join(dir, 'tasks.json'), tasks: tasks.map(task => ({ runId: task.runId, sessionId: task.sessionId })) }));
