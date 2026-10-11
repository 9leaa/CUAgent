/** Official plugin entry and image render path; HTTP/attachments are simulated. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtempSync, writeFileSync, readFileSync, rmSync, realpathSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createHash } from 'node:crypto'
import { apply } from './c0-vm-tools.ts'
import { createImageProbePngFor } from '../image-probe.mjs'

function fixture(t: any, change: any = {}) {
  const root=realpathSync(mkdtempSync(join(tmpdir(),'calc-dsh-')))
  const old={connection:process.env.CUAGENT_C0_CONNECTION,audit:process.env.CUAGENT_C0_AUDIT_PATH,fetch:globalThis.fetch}
  t.after(()=>{globalThis.fetch=old.fetch; for (const [name,value] of [['CUAGENT_C0_CONNECTION',old.connection],['CUAGENT_C0_AUDIT_PATH',old.audit]]) {
    if(value===undefined) delete process.env[name!];else process.env[name!]=value
  } rmSync(root,{recursive:true,force:true})})
  const binding={url:'http://192.168.64.3:8766',token:'x'.repeat(43),caseId:'calc_selection',stage:'p7',protocol:'calc-selection-v1',
    runId:'calc-select-11111111-1111-1111-1111-111111111111',sessionId:'session-22222222-2222-2222-2222-222222222222',cell:'A2',...change}
  process.env.CUAGENT_C0_CONNECTION=join(root,'connection.json');process.env.CUAGENT_C0_AUDIT_PATH=join(root,'audit.jsonl')
  writeFileSync(process.env.CUAGENT_C0_CONNECTION,JSON.stringify(binding),{mode:0o600})
  const registered:any[]=[],guards:any[]=[],handlers=new Map(),calls:any[]=[]
  const png=createImageProbePngFor({'top-left':'red','top-right':'green','bottom-left':'blue','bottom-right':'yellow'})
  const image={attachmentId:'sha256:'+createHash('sha256').update(png).digest('hex'),mediaType:'image/png',bytes:png.length,width:96,height:64}
  const control:any={capable:true,corrupt:null,failImage:false,images:0}
  const route={provider:'deepseek-account',model:'deepseek-flash',reasoningEffort:'off'}
  const ctx:any={logger:{error(){}},inject(){},on:(name:string,fn:any)=>handlers.set(name,fn),
    tools:{register:(tool:any)=>registered.push(tool),guard:(fn:any)=>guards.push(fn)},
    get:(name:string)=>name==='llm'?{resolveModelInfo:async()=>({inputModalities:control.capable?['image','text']:['text']})}
      :name==='attachments'?{saveImage:async()=>{if(control.failImage)throw Error('attachment failed');control.images++;return image}}:undefined}
  const abort=new AbortController()
  const agent={session:{id:binding.sessionId,requestHeader:()=>({config:route})},options:route}
  const exec:any={agent,signal:abort.signal,concludeTurn(){control.concluded=true}}
  const state=(id:string)=>({snapshot_id:id,pid:10,window_id:20,window_title:'probe',app_name:'LibreOffice',
    screenshot_frame_valid:true,screenshot_width:96,screenshot_height:64,screenshot_scale:2,elements_complete:false})
  globalThis.fetch=(async(url:any,options:any)=>{
    assert.equal(url,binding.url)
    const body=JSON.parse(options.body);calls.push(body)
    assert.equal(body.runId,binding.runId);assert.equal(body.sessionId,binding.sessionId)
    if(body.op==='stop')return {ok:true,json:async()=>({stopped:true})}
    const common={protocol:binding.protocol,runId:binding.runId,sessionId:binding.sessionId,cell:'A2',inputPermitted:false,businessStatus:'UNVERIFIED'}
    let value:any
    if(body.op==='observe')value={...common,used:1,state:state('s00000001'),png:png.toString('base64')}
    else if(body.args.x===undefined)value={...common,used:1,status:'NEEDS_SCREENSHOT_POINT',snapshot_id:'s00000001'}
    else value={...common,used:3,status:'SELECTION_OBSERVED',state:state('s00000002'),png:png.toString('base64'),
      confirmation:{status:'SELECTION_OBSERVED',cell:'A2',snapshot_id:'s00000002',inputPermitted:false}}
    if(control.corrupt)value=control.corrupt(value)
    return {ok:true,json:async()=>value}
  }) as any
  return {root,binding,registered,guards,handlers,calls,ctx,exec,abort,control,route,image,init:()=>apply(ctx),
    tool:(name:string)=>registered.find(x=>x.name===name)}
}

test('official entry registers only Calc tools and emits images through fallback and confirmation',async t=>{
  const f=fixture(t);f.init()
  assert.deepEqual(f.registered.map(x=>x.name).sort(),['vm_calc_observe','vm_calc_select','vm_calc_stop'])
  await f.handlers.get('agent/pre-step')({agent:f.exec.agent,signal:f.exec.signal},async()=>{})
  const observation=await f.tool('vm_calc_observe').execute({},f.exec)
  const blocks=f.tool('vm_calc_observe').output.render({},observation)
  assert.equal(blocks[1].type,'image');assert.equal(blocks[1].attachment.attachmentId,f.image.attachmentId)
  assert.equal(JSON.parse(observation.result).snapshot_id,'s00000001')
  const fallback=await f.tool('vm_calc_select').execute({snapshot_id:'s00000001'},f.exec)
  assert.equal(JSON.parse(fallback.result).status,'NEEDS_SCREENSHOT_POINT');assert.equal(f.control.images,1)
  const options={...f.route,tools:f.registered,messages:[{content:blocks}]}
  for await(const _ of f.handlers.get('llm/stream')(options,async function*(){yield 'ok'})){}
  assert.deepEqual(JSON.parse(readFileSync(join(f.root,'audit.jsonl'),'utf8')).imageAttachmentIds,[f.image.attachmentId])
  const coords={snapshot_id:'s00000001',x:25,y:30}
  const selected=await f.tool('vm_calc_select').execute(coords,f.exec)
  assert.deepEqual(f.calls[2].args,coords) // No operator-produced coordinate substitution.
  assert.equal(JSON.parse(selected.result).status,'SELECTION_OBSERVED');assert.equal(f.control.concluded,true)
  assert.equal(JSON.parse(selected.result).businessStatus,'UNVERIFIED')
  assert.equal(JSON.parse(readFileSync(join(f.root,'calc-image-3.json'),'utf8')).snapshotId,'s00000002')
  await assert.rejects(f.tool('vm_calc_observe').execute({},f.exec),/stopped/)
  assert.equal(f.calls.length,3)
})

for(const change of [{sessionId:'wrong'},{runId:'wrong'},{stage:'c2'},{protocol:'other'},{cell:'A0'},{inputMode:'checked-draft-v1'},{caseId:'real_textedit'}]) {
  test('mixed/unbound Calc config rejected '+JSON.stringify(change),t=>{const f=fixture(t,change);assert.throws(f.init);assert.equal(f.registered.length,0)})
}

test('scope and route guards deny before dispatch',async t=>{
  const f=fixture(t);f.init()
  for(const change of [{agent:{session:{id:'other'}}},{parent:{}},{signal:AbortSignal.abort()}])
    await assert.rejects(f.tool('vm_calc_observe').execute({},{...f.exec,...change}))
  f.route.reasoningEffort='high'
  await assert.rejects(f.tool('vm_calc_observe').execute({},f.exec),/Flash/)
  assert.equal(f.calls.length,0)
  assert.ok(f.guards.some(g=>g({...f.exec,name:'vm_type'})))
})

test('cancel sends bound stop and prevents a later coordinate call',async t=>{
  const f=fixture(t);f.init();await f.tool('vm_calc_observe').execute({},f.exec)
  f.abort.abort();await new Promise(r=>setImmediate(r))
  assert.equal(f.calls.at(-1).op,'stop')
  await assert.rejects(f.tool('vm_calc_select').execute({snapshot_id:'s00000001',x:25,y:30},f.exec))
  assert.equal(f.calls.length,2)
})

for(const fault of ['identity','png','used','attachment','stale','extraArgs','missingImage']) {
  test('failed evidence or arguments stops without replay '+fault,async t=>{
    const f=fixture(t);f.init()
    if(fault==='identity') f.control.corrupt=(v:any)=>({...v,runId:'other'})
    if(fault==='png') f.control.corrupt=(v:any)=>({...v,png:'invalid'})
    if(fault==='used') f.control.corrupt=(v:any)=>({...v,used:31})
    if(fault==='attachment') f.control.failImage=true
    if(fault==='missingImage') f.control.capable=false
    if(['stale','extraArgs'].includes(fault)) {
      await f.tool('vm_calc_observe').execute({},f.exec)
      await assert.rejects(f.tool('vm_calc_select').execute(fault==='stale'?{snapshot_id:'old',x:25,y:30}:{snapshot_id:'s00000001',x:25,y:30,nameBoxIndex:2},f.exec))
    } else await assert.rejects(f.tool('vm_calc_observe').execute({},f.exec))
    assert.equal(f.calls.at(-1).op,'stop')
    const count=f.calls.length
    await assert.rejects(f.tool('vm_calc_observe').execute({},f.exec));assert.equal(f.calls.length,count)
  })
}

test('model request requires the current returned screenshot and exact Flash/off tools',async t=>{
  const f=fixture(t);f.init();const value=await f.tool('vm_calc_observe').execute({},f.exec)
  const stream=f.handlers.get('llm/stream')
  const options={...f.route,tools:f.registered,messages:[{content:f.tool('vm_calc_observe').output.render({},value)}]}
  for(const change of [{messages:[]},{reasoningEffort:'high'},{tools:[...f.registered,{name:'shell'}]},{model:'other'}])
    await assert.rejects(async()=>{for await(const _ of stream({...options,...change},async function*(){})){} })
})
