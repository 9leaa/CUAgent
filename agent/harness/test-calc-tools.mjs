/** Run adapter boundary tests in the installed official App runtime; no model/UI. */
import { mkdtempSync, mkdirSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { dirname, isAbsolute, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const [esbuildModule, app] = process.argv.slice(2)
if (!esbuildModule || !app || !isAbsolute(esbuildModule) || !isAbsolute(app)) {
  throw new Error('Usage: node agent/harness/test-calc-tools.mjs /absolute/esbuild/lib/main.js /absolute/DeepSeek-Harness.app')
}
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
mkdirSync(join(root,'.runtime'),{recursive:true,mode:0o700})
const outdir=mkdtempSync(join(root,'.runtime/calc-adapter-test-'))
const {build}=await import(pathToFileURL(esbuildModule).href)
await build({entryPoints:['calc-vm-tools.test.ts','c0-vm-tools.test.ts'].map(name=>join(root,'agent/harness',name)),
  outdir,outExtension:{'.js':'.mjs'},bundle:true,platform:'node',format:'esm',target:'node24',plugins:[{
    name:'installed-official-app',setup(b){b.onResolve({filter:/^@deepseek-ai\//},a=>({
      path:join(app,'Contents/Resources/app.asar/dsh/node_modules',a.path,'lib/index.js'),external:true}))},
  }]})
const result=spawnSync(join(app,'Contents/MacOS/DeepSeek Harness'),['--test',join(outdir,'calc-vm-tools.test.mjs'),join(outdir,'c0-vm-tools.test.mjs')],
  {env:{...process.env,ELECTRON_RUN_AS_NODE:'1'},stdio:'inherit'})
console.log('Retained test bundles:',outdir)
if (result.error) throw result.error
process.exitCode=result.status??1
