/** Offline preflight only: no App launch, account access, budget reset or file writes. */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadA1TaskConfig } from '../a1-task-config.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const path = process.argv[2];
if (process.argv.length !== 3) throw new Error('absolute private task config required');
loadA1TaskConfig(path);
const profile = `${root}/.runtime/desktop-home/profiles/desktop`;
const out = `${profile}/cuagent-a1-plugins`;
const manifest = JSON.parse(readFileSync(`${out}/build.json`, 'utf8'));
const entries = ['a1-policy-plugin', 'a1-tools', 'a1-request-audit', 'desktop-tool-scope', 'a1-example-fingerprint'];
if (manifest.stage !== 'a1' || manifest.appVersion !== '0.2.0-rc.2' || manifest.sourceCommit !== '639ed015'
  || JSON.stringify(Object.keys(manifest.hashes).sort()) !== JSON.stringify([...entries].sort())) throw new Error('A1 reviewed build required');
for (const entry of entries) if (createHash('sha256').update(readFileSync(`${out}/${entry}.mjs`)).digest('hex') !== manifest.hashes[entry]) throw new Error('A1 build hash mismatch');
const { load } = await import(`${root}/.runtime/desktop-build-tools/node_modules/js-yaml/index.js`);
const patch = load(readFileSync(`${profile}/cordis.patch.yml`, 'utf8'));
const rows = patch.flatMap(row => row.insert ?? [row]);
if (!rows.some(row => row.id === 'cuagent-a1-policy' && !row.disabled)
  || !rows.some(row => row.id === 'cuagent-a1-request-audit' && !row.disabled)
  || rows.find(row => row.id === 'agent-preset-registry')?.config?.default !== 'a1-controlled') throw new Error('configure the reviewed A1 profile before launch');
console.log('A1 launch preflight passed; budgets and existing artifacts unchanged');
