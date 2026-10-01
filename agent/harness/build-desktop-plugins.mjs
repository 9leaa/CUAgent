/** Build project adapters without copying or modifying the official app. */
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { resolve, dirname } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const { build } = await import(`${root}/.runtime/desktop-build-tools/node_modules/esbuild/lib/main.js`)
const outdir = `${root}/.runtime/desktop-home/profiles/desktop/cuagent-plugins`
mkdirSync(outdir, { recursive: true })
const entries = ['a0-policy-plugin', 'calculate', 'a0-file-tools', 'image-probe', 'desktop-request-audit', 'desktop-tool-scope']
if (process.argv.includes('--c0')) entries.push('c0-vm-tools')
await build({ entryPoints: entries.map(name => `${root}/agent/harness/${name}.ts`),
  outdir, outExtension: { '.js': '.mjs' }, bundle: true, platform: 'node',
  format: 'esm', target: 'node24', external: ['@deepseek-ai/*'], sourcemap: false })
const hashes = Object.fromEntries(entries.map(name => [name,
  createHash('sha256').update(readFileSync(`${outdir}/${name}.mjs`)).digest('hex')]))
writeFileSync(`${outdir}/build.json`, JSON.stringify({ appVersion: '0.2.0-rc.2',
  sourceCommit: '639ed015', esbuildVersion: '0.28.1', hashes }, null, 2) + '\n')
console.log(`Built ${entries.length} adapters for official Desktop 0.2.0-rc.2`)
