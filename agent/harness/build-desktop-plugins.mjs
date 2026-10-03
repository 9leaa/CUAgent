/** Build project adapters without copying or modifying the official app. */
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { resolve, dirname } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const { build } = await import(`${root}/.runtime/desktop-build-tools/node_modules/esbuild/lib/main.js`)
const stage = process.argv.includes('--a1') ? 'a1' : 'a0'
const outdir = `${root}/.runtime/desktop-home/profiles/desktop/${stage === 'a1' ? 'cuagent-a1-plugins' : 'cuagent-plugins'}`
mkdirSync(outdir, { recursive: true })
const entries = stage === 'a1' ? ['a1-policy-plugin', 'a1-tools', 'a1-request-audit', 'desktop-tool-scope', 'a1-example-fingerprint', 'report-inputs-tools']
  : ['a0-policy-plugin', 'calculate', 'a0-file-tools', 'image-probe', 'desktop-request-audit', 'desktop-tool-scope']
if (process.argv.includes('--a1') && process.argv.includes('--c0')) throw new Error('A1 and C0 are separate reviewed builds')
if (process.argv.includes('--c0')) entries.push('c0-vm-tools')
await build({ entryPoints: entries.map(name => `${root}/agent/harness/${name}.ts`),
  outdir, outExtension: { '.js': '.mjs' }, bundle: true, platform: 'node',
  format: 'esm', target: 'node24', external: ['@deepseek-ai/*'], sourcemap: false })
const hashes = Object.fromEntries(entries.map(name => [name,
  createHash('sha256').update(readFileSync(`${outdir}/${name}.mjs`)).digest('hex')]))
writeFileSync(`${outdir}/build.json`, JSON.stringify({ stage, appVersion: '0.2.0-rc.2',
  sourceCommit: '639ed015', esbuildVersion: '0.28.1', hashes }, null, 2) + '\n')
console.log(`Built ${entries.length} adapters for official Desktop 0.2.0-rc.2`)
