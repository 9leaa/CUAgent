/** Merge reviewed A0 entries while preserving account and UI configuration. */
import { readFileSync, writeFileSync, copyFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { spawnSync } from 'node:child_process'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const { load, dump } = await import(`${root}/.runtime/desktop-build-tools/node_modules/js-yaml/index.js`)
const profile = `${root}/.runtime/desktop-home/profiles/desktop`
const target = `${profile}/cordis.patch.yml`
const flags = process.argv.slice(2)
if (flags.length > 1 || flags.some(flag => !['--a1', '--c2', '--c1', '--c0-ui', '--c0'].includes(flag))) throw new Error('select one reviewed stage')
const stage = flags[0]?.slice(2) ?? 'a0'
if (stage === 'a1' && spawnSync('/usr/bin/pgrep', ['-f', '^/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness']).status === 0) throw new Error('Quit the App before changing stage; do not hot-switch a live run')
const additions = load(readFileSync(`${root}/agent/harness/cordis.desktop.${stage}.patch.yml`, 'utf8')
  .replaceAll('@@PLUGIN_URL@@', pathToFileURL(`${profile}/${stage === 'a1' ? 'cuagent-a1-plugins' : 'cuagent-plugins'}`).href))
const before = load(readFileSync(target, 'utf8')) ?? []
const controlledIds = new Set(additions.flatMap(row => row.insert?.map(child => child.id) ?? [row.id]))
for (const id of ['cuagent-a0-policy', 'preset-a0-verify', 'cuagent-desktop-request-audit', 'preset-c0-calculator', 'preset-c0-ui', 'preset-c1-controlled', 'preset-c2-controlled', 'c0-vm-tools', 'cuagent-a1-policy', 'preset-a1-controlled', 'preset-a1-readonly', 'cuagent-a1-request-audit']) controlledIds.add(id)
const retained = before.flatMap(row => {
  if (row.insert) {
    const insert = row.insert.filter(child => !controlledIds.has(child.id))
    return insert.length ? [{ ...row, insert }] : []
  }
  return controlledIds.has(row.id) ? [] : [row]
})
copyFileSync(target, `${target}.before-a0-${Date.now()}`)
writeFileSync(target, dump([...retained, ...additions], { lineWidth: 110 }), { mode: 0o600 })
console.log(`Desktop ${stage} profile configured; original patch backed up.`)
