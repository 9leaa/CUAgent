/** Merge reviewed A0 entries while preserving account and UI configuration. */
import { readFileSync, writeFileSync, copyFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const { load, dump } = await import(`${root}/.runtime/desktop-build-tools/node_modules/js-yaml/index.js`)
const profile = `${root}/.runtime/desktop-home/profiles/desktop`
const target = `${profile}/cordis.patch.yml`
const stage = process.argv.includes('--c2') ? 'c2' : process.argv.includes('--c1') ? 'c1' : process.argv.includes('--c0-ui') ? 'c0-ui' : process.argv.includes('--c0') ? 'c0' : 'a0'
const additions = load(readFileSync(`${root}/agent/harness/cordis.desktop.${stage}.patch.yml`, 'utf8')
  .replaceAll('@@PLUGIN_URL@@', pathToFileURL(`${profile}/cuagent-plugins`).href))
const before = load(readFileSync(target, 'utf8')) ?? []
const controlledIds = new Set(additions.flatMap(row => row.insert?.map(child => child.id) ?? [row.id]))
for (const id of ['cuagent-a0-policy', 'preset-a0-verify', 'cuagent-desktop-request-audit', 'preset-c0-calculator', 'preset-c0-ui', 'preset-c1-controlled', 'preset-c2-controlled', 'c0-vm-tools']) controlledIds.add(id)
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
