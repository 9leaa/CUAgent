/** No VM, model or credentials: adapter boundary tests only. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtempSync, writeFileSync, rmSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { apply } from './c0-vm-tools.ts'

test('C0 fixed tools, ownership, fresh image attachment, cancellation and no retry', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'cuagent-c0-test-'))
  const old = { connection: process.env.CUAGENT_C0_CONNECTION, audit: process.env.CUAGENT_C0_AUDIT_PATH, fetch: globalThis.fetch }
  t.after(() => {
    globalThis.fetch = old.fetch
    if (old.connection === undefined) delete process.env.CUAGENT_C0_CONNECTION
    else process.env.CUAGENT_C0_CONNECTION = old.connection
    if (old.audit === undefined) delete process.env.CUAGENT_C0_AUDIT_PATH
    else process.env.CUAGENT_C0_AUDIT_PATH = old.audit
    rmSync(dir, { recursive: true, force: true })
  })
  process.env.CUAGENT_C0_CONNECTION = join(dir, 'connection.json')
  process.env.CUAGENT_C0_AUDIT_PATH = join(dir, 'audit.jsonl')
  writeFileSync(process.env.CUAGENT_C0_CONNECTION, JSON.stringify({ url: 'http://192.168.64.3:8766', token: 'x'.repeat(43) }), { mode: 0o600 })
  const tools: any[] = [], handlers = new Map(), calls: string[] = []
  let guard: any, failed = false
  const attachment = { attachmentId: 'image-1', mediaType: 'image/png', bytes: 8, width: 1, height: 1 }
  const ctx: any = {
    inject() {},
    tools: { register: (tool: any) => tools.push(tool), guard: (fn: any) => { guard = fn } },
    on: (name: string, fn: any) => handlers.set(name, fn), logger: { error() {} },
    get: (name: string) => name === 'llm' ? { resolveModelInfo: async () => ({ inputModalities: ['image'] }) }
      : { saveImage: async ({ data }: any) => { assert.equal(data.length, 8); return attachment } },
  }
  globalThis.fetch = (async (url: any, options: any) => {
    assert.equal(url, 'http://192.168.64.3:8766')
    const { op } = JSON.parse(options.body); calls.push(op)
    if (failed && op !== 'stop') throw new Error('timeout')
    return { ok: true, json: async () => ({ state: { snapshot_id: 's' }, png: Buffer.from([137,80,78,71,13,10,26,10]).toString('base64') }) }
  }) as any
  apply(ctx)
  assert.deepEqual(tools.map(t => t.name), ['vm_observe','vm_click','vm_write_result','vm_read_result'])
  const signal = new AbortController()
  assert.match(guard({ name: 'vm_observe', signal: signal.signal }), /not authorized/)
  const agent: any = { session: { id: 's1', requestHeader: () => undefined }, options: { provider: 'test', model: 'image' } }
  await handlers.get('agent/pre-step')({ agent, signal: signal.signal }, async () => ({}))
  assert.match(guard({ name: 'shell', agent, signal: signal.signal }), /not allowed/)
  assert.match(guard({ name: 'vm_observe', agent: { session: { id: 'other' } }, signal: signal.signal }), /not authorized/)
  const observed = await tools[0].execute({}, { agent, signal: signal.signal })
  assert.equal(tools[0].output.render({}, observed)[1].type, 'image')
  assert.equal(observed.image.attachmentId, 'image-1')
  failed = true
  await assert.rejects(tools[1].execute({ snapshot_id: 's', element_index: 1, element_token: 't' }, { signal: signal.signal }), /timeout/)
  assert.equal(calls.filter(c => c === 'click').length, 1)
  signal.abort('user stop')
  await Promise.resolve()
  assert.equal(calls.at(-1), 'stop')
  assert.match(guard({ name: 'vm_observe', agent, signal: new AbortController().signal }), /stopped/)
  await assert.rejects(tools[0].execute({}, { agent, signal: new AbortController().signal }), /stopped/)
  assert.equal(calls.filter(c => c === 'observe').length, 1)
})

test('Real TextEdit is opt-in and registers only five narrow tools', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'cuagent-real-app-'))
  const oldConnection = process.env.CUAGENT_C0_CONNECTION, oldAudit = process.env.CUAGENT_C0_AUDIT_PATH
  t.after(() => {
    if (oldConnection === undefined) delete process.env.CUAGENT_C0_CONNECTION; else process.env.CUAGENT_C0_CONNECTION = oldConnection
    if (oldAudit === undefined) delete process.env.CUAGENT_C0_AUDIT_PATH; else process.env.CUAGENT_C0_AUDIT_PATH = oldAudit
    rmSync(dir, { recursive: true, force: true })
  })
  process.env.CUAGENT_C0_CONNECTION = join(dir, 'connection.json')
  process.env.CUAGENT_C0_AUDIT_PATH = join(dir, 'audit.jsonl')
  writeFileSync(process.env.CUAGENT_C0_CONNECTION, JSON.stringify({ url: 'http://192.168.64.3:8766', token: 'x'.repeat(43), caseId: 'real_textedit' }), { mode: 0o600 })
  const registered: any[] = [], handlers = new Map(); let guard: any
  const ctx: any = { inject() {}, on: (name: string, fn: any) => handlers.set(name, fn), logger: { error() {} },
    tools: { register: (tool: any) => registered.push(tool), guard: (fn: any) => { guard = fn } } }
  apply(ctx)
  assert.deepEqual(registered.map(tool => tool.name), ['vm_observe', 'vm_write_result', 'vm_read_result', 'vm_type', 'vm_save'])
  const agent: any = { session: { id: 'real-owner' } }, signal = new AbortController().signal
  await handlers.get('agent/pre-step')({ agent, signal }, async () => ({}))
  for (const name of ['vm_click', 'vm_scroll', 'vm_select_target', 'shell', 'control', 'verify']) assert.match(guard({ name, agent, signal }), /not allowed/)
  assert.equal(guard({ name: 'vm_save', agent, signal }), undefined)
})

test('C1 cases add only reviewed target selection and necessary typing', async t => {
  const dir=mkdtempSync(join(tmpdir(),'cuagent-c1-tools-'))
  const previous={connection:process.env.CUAGENT_C0_CONNECTION,audit:process.env.CUAGENT_C0_AUDIT_PATH,fetch:globalThis.fetch}
  t.after(()=>{
    globalThis.fetch=previous.fetch
    for(const [key,value] of [['CUAGENT_C0_CONNECTION',previous.connection],['CUAGENT_C0_AUDIT_PATH',previous.audit]]) {
      if(value===undefined)delete process.env[key!];else process.env[key!]=value
    }
    rmSync(dir,{recursive:true,force:true})
  })
  process.env.CUAGENT_C0_CONNECTION=join(dir,'connection.json')
  process.env.CUAGENT_C0_AUDIT_PATH=join(dir,'audit.jsonl')
  const calls:string[]=[]
  globalThis.fetch=(async (_url:any,options:any)=>{
    calls.push(JSON.parse(options.body).op)
    return {ok:true,json:async()=>({selected:'CUAgent Destination',requires_new_observation:true})}
  }) as any
  for(const caseId of ['cross_app','popup','window_change','input_correction','long_workflow','reobserve_failure']){
    writeFileSync(process.env.CUAGENT_C0_CONNECTION,JSON.stringify({url:'http://192.168.64.3:8766',token:'x'.repeat(43),caseId}),{mode:0o600})
    const registered:any[]=[],handlers=new Map();let guard:any
    const ctx:any={inject(){},on:(name:string,fn:any)=>handlers.set(name,fn),logger:{error(){}},
      tools:{register:(tool:any)=>registered.push(tool),guard:(fn:any)=>{guard=fn}}}
    apply(ctx)
    assert.deepEqual(registered.map(x=>x.name),['vm_observe','vm_click','vm_write_result','vm_read_result',
      ...(caseId==='popup'?[]:['vm_type']),'vm_select_target'])
    const signal=new AbortController().signal,agent:any={session:{id:'owner'}}
    await handlers.get('agent/pre-step')({agent,signal},async()=>({}))
    assert.match(guard({name:'vm_scroll',agent,signal}),/not allowed/)
    assert.match(guard({name:'shell',agent,signal}),/not allowed/)
    assert.equal(guard({name:'vm_select_target',agent,signal}),undefined)
    await registered.find(x=>x.name==='vm_select_target').execute({target:'CUAgent Destination'},{agent,signal})
  }
  assert.deepEqual(calls,Array(6).fill('select_target'))
})

test('C2 carries actual session/epoch, propagates paused state, and adds no control tools', async t => {
  const dir=mkdtempSync(join(tmpdir(),'cuagent-c2-tools-'))
  const previous={connection:process.env.CUAGENT_C0_CONNECTION,audit:process.env.CUAGENT_C0_AUDIT_PATH,fetch:globalThis.fetch}
  t.after(()=>{
    globalThis.fetch=previous.fetch
    for(const [key,value] of [['CUAGENT_C0_CONNECTION',previous.connection],['CUAGENT_C0_AUDIT_PATH',previous.audit]]) {
      if(value===undefined)delete process.env[key!];else process.env[key!]=value
    }
    rmSync(dir,{recursive:true,force:true})
  })
  process.env.CUAGENT_C0_CONNECTION=join(dir,'connection.json')
  process.env.CUAGENT_C0_AUDIT_PATH=join(dir,'audit.jsonl')
  writeFileSync(process.env.CUAGENT_C0_CONNECTION,JSON.stringify({url:'http://192.168.64.3:8766',token:'x'.repeat(43),caseId:'input_correction',stage:'c2',epoch:7}),{mode:0o600})
  const registered:any[]=[],handlers=new Map(),calls:any[]=[];let guard:any
  const ctx:any={inject(){},on:(name:string,fn:any)=>handlers.set(name,fn),logger:{error(){}},
    tools:{register:(tool:any)=>registered.push(tool),guard:(fn:any)=>{guard=fn}}}
  globalThis.fetch=(async (_url:any,options:any)=>{
    const body=JSON.parse(options.body);calls.push(body)
    assert.equal(body.session_id,'session-owner')
    if(calls.length===1){assert.equal(body.epoch,7);return {ok:true,json:async()=>({control_epoch:8,stopped:false,content:'actual'})}}
    assert.equal(body.epoch,8)
    return {ok:false,json:async()=>({control_epoch:9,stopped:true,error:'Task paused after UNKNOWN'})}
  }) as any
  apply(ctx)
  assert.deepEqual(registered.map(x=>x.name),['vm_observe','vm_click','vm_write_result','vm_read_result','vm_type','vm_select_target'])
  const signal=new AbortController().signal,agent:any={session:{id:'session-owner'}}
  await handlers.get('agent/pre-step')({agent,signal},async()=>({}))
  const read=registered.find(x=>x.name==='vm_read_result')
  await read.execute({},{agent,signal})
  await assert.rejects(read.execute({},{agent,signal}),/paused after UNKNOWN/)
  assert.match(guard({name:'vm_observe',agent,signal}),/stopped/)
  await assert.rejects(read.execute({},{agent,signal}),/stopped/)
  assert.equal(calls.length,2)
})

test('C2 controlled model error requires a tool image, stops, and persists once across restart', async t => {
  const dir=mkdtempSync(join(tmpdir(),'cuagent-model-fault-'))
  const previous={connection:process.env.CUAGENT_C0_CONNECTION,audit:process.env.CUAGENT_C0_AUDIT_PATH,fetch:globalThis.fetch}
  t.after(()=>{
    globalThis.fetch=previous.fetch
    for(const [key,value] of [['CUAGENT_C0_CONNECTION',previous.connection],['CUAGENT_C0_AUDIT_PATH',previous.audit]]) {
      if(value===undefined)delete process.env[key!];else process.env[key!]=value
    }
    rmSync(dir,{recursive:true,force:true})
  })
  process.env.CUAGENT_C0_CONNECTION=join(dir,'connection.json')
  process.env.CUAGENT_C0_AUDIT_PATH=join(dir,'audit.jsonl')
  const config={url:'http://192.168.64.3:8766',token:'x'.repeat(43),caseId:'input_correction',stage:'c2',epoch:1,modelFault:'after_first_observation'}
  writeFileSync(process.env.CUAGENT_C0_CONNECTION,JSON.stringify(config),{mode:0o600})
  const calls:any[]=[]
  globalThis.fetch=(async (_url:any,options:any)=>{
    calls.push(JSON.parse(options.body))
    return {ok:true,json:async()=>({stopped:true,control_epoch:2})}
  }) as any
  function context(){
    const handlers=new Map();let guard:any
    const ctx:any={inject(){},on:(name:string,fn:any)=>handlers.set(name,fn),logger:{error(){}},
      tools:{register(){},guard:(fn:any)=>{guard=fn}}}
    apply(ctx);return {handlers,get guard(){return guard}}
  }
  const first=context(),signal=new AbortController().signal,agent:any={session:{id:'session-first'}}
  await first.handlers.get('agent/pre-step')({agent,signal},async()=>({}))
  const plain={provider:'test',model:'image',tools:[{name:'vm_observe'}],messages:[]}
  let streamed=0
  const next=async function*(){streamed++;yield {type:'mock'}}
  for await(const _ of first.handlers.get('llm/stream')(plain,next)){}
  assert.equal(streamed,1);assert.equal(calls.length,0)
  const pictured={...plain,messages:[{content:[{type:'image'}]}]}
  await assert.rejects(async()=>{for await(const _ of first.handlers.get('llm/stream')(pictured,next)){}},/controlled model stream failure/)
  assert.equal(streamed,1);assert.deepEqual(calls.map(r=>r.op),['stop'])
  assert.equal(calls[0].session_id,'session-first')
  assert.match(first.guard({name:'vm_observe',agent,signal}),/stopped/)
  const marker=readFileSync(join(dir,'model-fault.json'),'utf8')
  assert.equal(JSON.parse(marker).sessionId,'session-first')
  const restored=context(),resumed:any={session:{id:'session-resumed'}}
  await restored.handlers.get('agent/pre-step')({agent:resumed,signal},async()=>({}))
  for await(const _ of restored.handlers.get('llm/stream')(pictured,next)){}
  assert.equal(streamed,2);assert.equal(readFileSync(join(dir,'model-fault.json'),'utf8'),marker)
  writeFileSync(process.env.CUAGENT_C0_CONNECTION,JSON.stringify({...config,stage:'c0'}),{mode:0o600})
  assert.throws(()=>context(),/Unreviewed model fault/)
})
