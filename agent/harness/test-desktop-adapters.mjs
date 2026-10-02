/** Build tests against the installed official App; never modify its runtime/profile. */
import { mkdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const selected = process.argv.slice(2)
const permitted = new Set(['a0-policy.test.ts', 'a0-policy.integration.test.ts',
  'a0-file-tools.integration.test.ts', 'c0-vm-tools.test.ts', 'a1-csv-tools.integration.test.ts', 'a1-policy.integration.test.ts'])
if (selected.length === 0 || selected.some(file => !permitted.has(file))) {
  throw new Error('usage: node agent/harness/test-desktop-adapters.mjs <reviewed-test.ts> [...]')
}
const app = '/Applications/DeepSeek Harness.app'
const version = spawnSync('/usr/libexec/PlistBuddy', ['-c', 'Print:CFBundleShortVersionString', app + '/Contents/Info.plist'], { encoding: 'utf8' })
if (version.status !== 0 || version.stdout.trim() !== '0.2.0-rc.2') throw new Error('Official App version needs compatibility review')
const { build } = await import(root + '/.runtime/desktop-build-tools/node_modules/esbuild/lib/main.js')
const out = root + '/.runtime/a1-adapter-tests'
mkdirSync(out, { recursive: true, mode: 0o700 })
const official = app + '/Contents/Resources/app.asar/dsh/node_modules/'
const outputs = []
for (const file of selected) {
  readFileSync(root + '/agent/harness/' + file)
  const target = out + '/' + file.replace(/\.ts$/, '.mjs')
  await build({ entryPoints: [root + '/agent/harness/' + file], outfile: target,
    bundle: true, platform: 'node', format: 'esm', target: 'node24',
    plugins: [{ name: 'official-app-imports', setup(b) {
      b.onResolve({ filter: /^@deepseek-ai\// }, args => ({ path: official + args.path + '/lib/index.js', external: true }))
    } }],
  })
  outputs.push(target)
}
const result = spawnSync(app + '/Contents/MacOS/DeepSeek Harness', ['--expose-internals', '--test', ...outputs], {
  cwd: root, env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' }, stdio: 'inherit',
})
process.exit(result.status ?? 1)
