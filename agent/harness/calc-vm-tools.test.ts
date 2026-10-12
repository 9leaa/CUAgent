/** Official plugin entry and image render path; HTTP/attachments are simulated. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtempSync, writeFileSync, readFileSync, rmSync, realpathSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createHash } from 'node:crypto'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { apply } from './c0-vm-tools.ts'
import { createImageProbePngFor } from '../image-probe.mjs'
import { deriveDetail, detailRegion, originalPoint } from './calc-image-detail.ts'

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
      :name==='attachments'?{saveImage:async(input:any)=>{if(control.failImage)throw Error('attachment failed');control.images++;
        if(control.dynamicImages){const b=Buffer.from(input.data);return {attachmentId:'sha256:'+createHash('sha256').update(b).digest('hex'),mediaType:'image/png',bytes:b.length,width:b.readUInt32BE(16),height:b.readUInt32BE(20)}}
        return image}}:undefined}
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
    if(control.reply)value=control.reply(body,{common,state,png},value)
    if(control.corrupt)value=control.corrupt(value)
    return {ok:true,json:async()=>value}
  }) as any
  return {root,binding,registered,guards,handlers,calls,ctx,exec,abort,control,route,image,init:()=>apply(ctx),
    tool:(name:string)=>registered.find(x=>x.name===name)}
}

async function inputFixture(t:any, saveMode=false, activation=false) {
  const f=fixture(t,{protocol:saveMode?'calc-save-v1':'calc-input-v1',approvedText:'AbZ中文',approvedKind:'text',...(activation?{activationApproved:true}:{})});f.init()
  f.control.reply=(body:any,{common,state,png}:any,value:any)=>{
    if(body.op==='input_cell')return {...common,used:5,status:'INPUT_OBSERVED',state:state('s00000003'),png:png.toString('base64'),
      confirmation:{status:'INPUT_OBSERVED',cell:'A2',snapshot_id:'s00000003',text:'AbZ中文',kind:'text',inputEffectVerified:true,storageTypeVerified:false,commitPermitted:false}}
    if(body.op==='open_save_dialog')return {...common,used:9,status:'SAVE_DIALOG_ATTEMPT_OBSERVED',state:state('s00000005'),png:png.toString('base64'),saved:false,savePermitted:false}
    if(body.op==='commit_cell' && saveMode)return {...common,used:7,status:'CELL_COMMIT_OBSERVED',state:state('s00000004'),png:png.toString('base64'),
      commitEffectVerified:true,saved:false,confirmation:{status:'CELL_COMMIT_OBSERVED',cell:'A2',snapshot_id:'s00000004',
        text:'AbZ中文',kind:'text',commitEffectVerified:true,saved:false,storageTypeVerified:false}}
    if(body.op==='commit_cell')return {...common,used:7,status:'COMMIT_ATTEMPT_OBSERVED',state:state('s00000004'),png:png.toString('base64'),
      commitEffectVerified:false,storageTypeVerified:false,commitPermitted:false}
    return value
  }
  await f.tool('vm_calc_observe').execute({},f.exec)
  await f.tool('vm_calc_select').execute({snapshot_id:'s00000001',x:25,y:30},f.exec)
  return f
}

for (const fault of [null,'extra','stale-args','stale-image','proof','accounting','repeat','timeout']) test(`explicit activation ${fault}`,async t=>{
  const f=await inputFixture(t,true,true)
  assert.equal(f.registered.length,8)
  const ready=JSON.parse(readFileSync(join(f.root,'vm-tools-ready.json'),'utf8'))
  assert.equal(ready.activationApproved,true);assert.ok(ready.toolNames.includes('vm_calc_activate'))
  f.control.reply=(body:any,{common,state,png}:any,value:any)=>{
    if(body.op==='activate_window') {
      if(fault==='timeout')throw Error('unknown delivery')
      return {...common,used:fault==='accounting'?4:5,status:'WINDOW_ACTIVATION_OBSERVED',
        state:state(fault==='stale-image'?'s00000002':'s00000003'),png:png.toString('base64'),inputEffectVerified:false,commitPermitted:false,
        confirmation:{status:'WINDOW_ACTIVATION_OBSERVED',cell:'A2',snapshot_id:'s00000003',inputEffectVerified:fault==='proof',inputPermitted:false,commitPermitted:false}}
    }
    if(body.op==='focus_input')return {...common,used:7,status:'INPUT_FOCUS_OBSERVED',state:state('s00000004'),png:png.toString('base64'),
      inputEffectVerified:false,commitPermitted:false,confirmation:{status:'INPUT_FOCUS_OBSERVED',cell:'A2',snapshot_id:'s00000004',inputEffectVerified:false,inputPermitted:false,commitPermitted:false}}
    return value
  }
  const args:any={snapshot_id:fault==='stale-args'?'old':'s00000002'}
  if(fault==='extra')args.pid=10
  if(fault && fault!=='repeat') {
    await assert.rejects(()=>f.tool('vm_calc_activate').execute(args,f.exec))
    assert.equal(f.calls.at(-1).op,'stop');return
  }
  const out=await f.tool('vm_calc_activate').execute(args,f.exec)
  assert.equal(JSON.parse(out.result).status,'WINDOW_ACTIVATION_OBSERVED');assert.ok(out.image)
  if(fault==='repeat') {
    await assert.rejects(()=>f.tool('vm_calc_activate').execute({snapshot_id:'s00000003'},f.exec))
    assert.equal(f.calls.filter(c=>c.op==='activate_window').length,1);return
  }
  const focused=await f.tool('vm_calc_focus').execute({snapshot_id:'s00000003',x:25,y:30},f.exec)
  assert.equal(JSON.parse(focused.result).used,7)
})

for (const binding of [
  {activationApproved:true},
  {protocol:'calc-input-v1',approvedText:'a',approvedKind:'text',activationApproved:false},
  {protocol:'calc-input-v1',approvedText:'a',approvedKind:'text',activationApproved:'true'},
]) test(`invalid activation binding ${JSON.stringify(binding)}`,t=>{
  const f=fixture(t,binding);assert.throws(()=>f.init());assert.equal(f.calls.length,0)
})

test('default input has no activation tool',async t=>{
  const f=await inputFixture(t)
  assert.equal(f.tool('vm_calc_activate'),undefined)
  assert.equal(Object.hasOwn(JSON.parse(readFileSync(join(f.root,'vm-tools-ready.json'),'utf8')),'activationApproved'),false)
})

for (const fault of ['early','budget']) test(`activation pre-dispatch guard ${fault}`,async t=>{
  const f=fixture(t,{protocol:'calc-input-v1',approvedText:'a',approvedKind:'text',activationApproved:true});f.init()
  f.control.reply=(body:any,_helpers:any,value:any)=>{
    if(fault==='budget')value.used=body.op==='observe'?21:23
    return value
  }
  await f.tool('vm_calc_observe').execute({},f.exec)
  if(fault==='budget')await f.tool('vm_calc_select').execute({snapshot_id:'s00000001',x:25,y:30},f.exec)
  await assert.rejects(()=>f.tool('vm_calc_activate').execute({snapshot_id:fault==='early'?'s00000001':'s00000002'},f.exec))
  assert.equal(f.calls.filter(c=>c.op==='activate_window').length,0)
  assert.equal(f.calls.at(-1).op,'stop')
})

for (const fault of [null,'nan','partial','extra','proof','accounting','stale','repeat','observe']) test(`focus tool bounded chain ${fault}`,async t=>{
  const f=await inputFixture(t,true)
  const prior=f.control.reply
  f.control.reply=(body:any,helpers:any,value:any)=>{
    const {common,state,png}=helpers
    if(body.op==='focus_input')return {...common,used:fault==='accounting'?4:5,
      status:'INPUT_FOCUS_OBSERVED',state:state(fault==='stale'?'s00000002':'s00000003'),png:png.toString('base64'),
      inputEffectVerified:false,commitPermitted:false,
      confirmation:{status:'INPUT_FOCUS_OBSERVED',cell:'A2',snapshot_id:'s00000003',inputEffectVerified:fault==='proof',inputPermitted:false,commitPermitted:false}}
    if(body.op==='observe')return {...common,used:6,state:state('s00000004'),png:png.toString('base64')}
    const result=prior(body,helpers,value)
    if(['input_cell','commit_cell','open_save_dialog'].includes(body.op)) {
      result.used+=2
      result.state.snapshot_id='s'+(Number.parseInt(result.state.snapshot_id.slice(1),16)+1).toString(16).padStart(8,'0')
      if(result.confirmation)result.confirmation.snapshot_id=result.state.snapshot_id
    }
    return result
  }
  const args:any={snapshot_id:'s00000002',x:25,y:30}
  if(fault==='nan')args.x=NaN
  if(fault==='partial')delete args.y
  if(fault==='extra')args.expected_text='a'
  if(fault && !['repeat','observe'].includes(fault)) {
    await assert.rejects(()=>f.tool('vm_calc_focus').execute(args,f.exec))
    assert.equal(f.calls.at(-1).op,'stop');return
  }
  const focused=await f.tool('vm_calc_focus').execute(args,f.exec)
  assert.equal(JSON.parse(focused.result).status,'INPUT_FOCUS_OBSERVED');assert.ok(focused.image)
  assert.deepEqual(f.calls.at(-1).args,args)
  if(fault==='repeat') {
    await assert.rejects(()=>f.tool('vm_calc_focus').execute({...args,snapshot_id:'s00000003'},f.exec))
    assert.equal(f.calls.filter(c=>c.op==='focus_input').length,1);return
  }
  if(fault==='observe') {
    await f.tool('vm_calc_observe').execute({},f.exec)
    await assert.rejects(()=>f.tool('vm_calc_input').execute({snapshot_id:'s00000004',text:'AbZ中文',kind:'text'},f.exec))
    assert.equal(f.calls.filter(c=>c.op==='input_cell').length,0);return
  }
  await f.tool('vm_calc_input').execute({snapshot_id:'s00000003',text:'AbZ中文',kind:'text'},f.exec)
  await f.tool('vm_calc_commit').execute({snapshot_id:'s00000004'},f.exec)
  const opened=await f.tool('vm_calc_open_save').execute({snapshot_id:'s00000005',x:20,y:30},f.exec)
  assert.equal(JSON.parse(opened.result).used,11)
  assert.equal(JSON.parse(opened.result).businessStatus,'UNVERIFIED')
})

test('explicit save protocol confirms commit then opens once with new image',async t=>{
  const f=await inputFixture(t,true)
  assert.equal(f.registered.length,7)
  assert.match(f.tool('vm_calc_focus').description,/visible existing formula text itself/)
  assert.match(f.tool('vm_calc_focus').description,/never choose the empty middle/)
  await f.tool('vm_calc_input').execute({snapshot_id:'s00000002',text:'AbZ中文',kind:'text'},f.exec)
  const committed=await f.tool('vm_calc_commit').execute({snapshot_id:'s00000003'},f.exec)
  assert.equal(JSON.parse(committed.result).status,'CELL_COMMIT_OBSERVED')
  assert.equal(f.control.concluded,undefined)
  const opened=await f.tool('vm_calc_open_save').execute({snapshot_id:'s00000004',x:20,y:30},f.exec)
  assert.deepEqual(f.calls.at(-1).args,{snapshot_id:'s00000004',x:20,y:30})
  assert.equal(JSON.parse(opened.result).status,'SAVE_DIALOG_ATTEMPT_OBSERVED');assert.ok(opened.image)
  assert.equal(JSON.parse(opened.result).businessStatus,'UNVERIFIED')
  await assert.rejects(()=>f.tool('vm_calc_open_save').execute({snapshot_id:'s00000005'},f.exec))
  assert.equal(f.calls.filter(c=>c.op==='open_save_dialog').length,1)
})

for(const fault of ['early','path','old','commit_proof','saved_claim','accounting','image','nan','partial'])test(`save protocol rejects ${fault}`,async t=>{
  const f=await inputFixture(t,true)
  if(fault==='early') {
    await assert.rejects(()=>f.tool('vm_calc_open_save').execute({snapshot_id:'s00000002'},f.exec))
    assert.equal(f.calls.filter(c=>c.op==='open_save_dialog').length,0);return
  }
  await f.tool('vm_calc_input').execute({snapshot_id:'s00000002',text:'AbZ中文',kind:'text'},f.exec)
  if(fault==='commit_proof') {
    f.control.corrupt=(v:any)=>({...v,confirmation:{...v.confirmation,text:'wrong'}})
    await assert.rejects(()=>f.tool('vm_calc_commit').execute({snapshot_id:'s00000003'},f.exec));return
  }
  await f.tool('vm_calc_commit').execute({snapshot_id:'s00000003'},f.exec)
  const args:any={snapshot_id:fault==='old'?'s00000003':'s00000004'}
  if(fault==='path')args.destination='/tmp/other.ods'
  if(fault==='nan')Object.assign(args,{x:NaN,y:20})
  if(fault==='partial')args.x=20
  if(fault==='saved_claim')f.control.corrupt=(v:any)=>({...v,saved:true})
  if(fault==='accounting')f.control.corrupt=(v:any)=>({...v,used:8})
  if(fault==='image')f.control.corrupt=(v:any)=>({...v,state:{...v.state,snapshot_id:'s00000004'}})
  await assert.rejects(()=>f.tool('vm_calc_open_save').execute(args,f.exec))
  assert.equal(f.calls.at(-1).op,'stop')
})

test('already-selected input route requires a fresh image and exactly one observation',async t=>{
  const f=fixture(t,{protocol:'calc-input-v1',approvedText:'AbZ中文',approvedKind:'text'});f.init()
  f.control.reply=(body:any,{common,state,png}:any,value:any)=>body.op==='select_cell'?{
    ...common,used:2,status:'SELECTION_OBSERVED',selectionRoute:'already-selected',state:state('s00000002'),png:png.toString('base64'),
    confirmation:{status:'SELECTION_OBSERVED',cell:'A2',snapshot_id:'s00000002',inputPermitted:false}}:value
  await f.tool('vm_calc_observe').execute({},f.exec)
  const result=await f.tool('vm_calc_select').execute({snapshot_id:'s00000001'},f.exec)
  assert.equal(JSON.parse(result.result).used,2);assert.ok(result.image)
  assert.equal(f.control.concluded,undefined)
})

for(const fault of ['legacy','coordinates','accounting','stale'])test(`readonly selection rejects ${fault}`,async t=>{
  const f=fixture(t,fault==='legacy'?{}:{protocol:'calc-input-v1',approvedText:'AbZ中文',approvedKind:'text'});f.init()
  f.control.reply=(body:any,{common,state,png}:any,value:any)=>body.op==='select_cell'?{
    ...common,used:fault==='accounting'?3:2,status:'SELECTION_OBSERVED',selectionRoute:'already-selected',
    state:state(fault==='stale'?'s00000001':'s00000002'),png:png.toString('base64'),
    confirmation:{status:'SELECTION_OBSERVED',cell:'A2',snapshot_id:'s00000002',inputPermitted:false}}:value
  await f.tool('vm_calc_observe').execute({},f.exec)
  await assert.rejects(()=>f.tool('vm_calc_select').execute({snapshot_id:'s00000001',...(fault==='coordinates'?{x:25,y:30}:{})},f.exec))
  assert.equal(f.calls.at(-1).op,'stop')
})

test('explicit input protocol keeps selection alive and ends after one commit image',async t=>{
  const f=await inputFixture(t)
  assert.equal(f.registered.length,6);assert.equal(f.control.concluded,undefined)
  const value=await f.tool('vm_calc_input').execute({snapshot_id:'s00000002',text:'AbZ中文',kind:'text'},f.exec)
  assert.equal(JSON.parse(value.result).status,'INPUT_OBSERVED');assert.ok(value.image)
  assert.equal(f.control.concluded,undefined)
  const result=await f.tool('vm_calc_commit').execute({snapshot_id:'s00000003'},f.exec)
  assert.equal(JSON.parse(result.result).used,7);assert.ok(result.image);assert.equal(f.control.concluded,true)
  assert.deepEqual(f.calls.map(c=>c.op),['observe','select_cell','input_cell','commit_cell'])
})

for(const fault of ['payload','old','early_commit','proof','budget','image','commit_claim'])test(`input protocol refuses ${fault}`,async t=>{
  const f=await inputFixture(t)
  const args={snapshot_id:'s00000002',text:'AbZ中文',kind:'text'}
  if(fault==='payload')args.text='other'
  if(fault==='old')args.snapshot_id='old'
  if(fault==='early_commit') {
    await assert.rejects(()=>f.tool('vm_calc_commit').execute({snapshot_id:'s00000002'},f.exec));return
  }
  if(fault==='proof')f.control.corrupt=(v:any)=>({...v,confirmation:{...v.confirmation,text:'abz中文'}})
  if(fault==='budget')f.control.corrupt=(v:any)=>({...v,used:6})
  if(fault==='image')f.control.corrupt=(v:any)=>({...v,png:undefined})
  if(fault==='commit_claim') {
    await f.tool('vm_calc_input').execute(args,f.exec)
    f.control.corrupt=(v:any)=>({...v,commitEffectVerified:true})
    await assert.rejects(()=>f.tool('vm_calc_commit').execute({snapshot_id:'s00000003'},f.exec))
  } else await assert.rejects(()=>f.tool('vm_calc_input').execute(args,f.exec))
  assert.equal(f.calls.at(-1).op,'stop');assert.equal(f.control.concluded,undefined)
})

test('offered edit cancellation returns fresh image before a separate model selection',async t=>{
  const f=fixture(t);f.init()
  let cancelled=false
  f.control.reply=(body:any,{common,state,png}:any,value:any)=>{
    if(body.op==='observe')return value
    if(body.args.cancel_edit){cancelled=true;return {...common,used:3,status:'EDIT_CANCEL_ATTEMPT_OBSERVED',state:state('s00000002'),png:png.toString('base64')}}
    if(body.args.x===undefined)return {...common,used:cancelled?3:1,status:cancelled?'NEEDS_SCREENSHOT_POINT':'NEEDS_EDIT_CANCEL',snapshot_id:cancelled?'s00000002':'s00000001'}
    return {...common,used:5,status:'SELECTION_OBSERVED',state:state('s00000003'),png:png.toString('base64'),
      confirmation:{status:'SELECTION_OBSERVED',cell:'A2',snapshot_id:'s00000003',inputPermitted:false}}
  }
  const select=(args:any)=>f.tool('vm_calc_select').execute(args,f.exec)
  await f.tool('vm_calc_observe').execute({},f.exec)
  assert.equal(JSON.parse((await select({snapshot_id:'s00000001'})).result).status,'NEEDS_EDIT_CANCEL')
  const cancelledResult=await select({snapshot_id:'s00000001',cancel_edit:true})
  assert.equal(JSON.parse(cancelledResult.result).status,'EDIT_CANCEL_ATTEMPT_OBSERVED')
  assert.ok(cancelledResult.image);assert.equal(f.control.concluded,undefined)
  await select({snapshot_id:'s00000002'})
  const result=await select({snapshot_id:'s00000002',x:25,y:30})
  assert.equal(JSON.parse(result.result).used,5);assert.equal(f.control.concluded,true)
  assert.equal(f.control.images,3)
})

test('official sharp decodes exact source and derives bounded 2x detail',async()=>{
  const png=createImageProbePngFor({'top-left':'red','top-right':'green','bottom-left':'blue','bottom-right':'yellow'})
  const result=await deriveDetail(png,{left:0,top:0,width:32,height:16},96,64)
  assert.equal(result.bytes.readUInt32BE(16),64);assert.equal(result.bytes.readUInt32BE(20),32)
  assert.equal(result.sourceSha256,createHash('sha256').update(png).digest('hex'))
  assert.deepEqual(originalPoint(result.geometry,20,10),{x:10,y:5})
  const sharp=createRequire(resolve(dirname(process.execPath),'../Resources/app.asar/dsh/package.json'))('sharp')
  const original=await sharp(png).removeAlpha().raw().toBuffer()
  const zoom=await sharp(result.bytes).removeAlpha().raw().toBuffer()
  for(let y=0;y<32;y++)for(let x=0;x<64;x++){
    const source=(Math.floor(y/2)*96+Math.floor(x/2))*3,target=(y*64+x)*3
    assert.deepEqual(zoom.subarray(target,target+3),original.subarray(source,source+3))
  }
  await assert.rejects(deriveDetail(png,{left:0,top:0,width:32,height:16},97,64))
})

for(const region of [{left:-1,top:0,width:32,height:16},{left:0,top:0,width:97,height:16},
  {left:0,top:0,width:32,height:15},{left:0,top:0,width:32,height:16,path:'/tmp/other'},
  {left:0.5,top:0,width:32,height:16},{left:0,top:NaN,width:32,height:16}]) {
  test('detail region refuses '+JSON.stringify(region),()=>assert.throws(()=>detailRegion(region,96,64)))
}

test('detail coordinates are finite inside enlarged crop',()=>{
  const geometry=detailRegion({left:10,top:20,width:32,height:16},96,64)
  assert.deepEqual(originalPoint(geometry,63,31),{x:41.5,y:35.5})
  for(const [x,y] of [[64,0],[0,32],[-1,0],[NaN,0],[0,Infinity]])assert.throws(()=>originalPoint(geometry,x,y))
  assert.throws(()=>originalPoint(undefined,0,0))
})

test('detail reaches model as a second image and maps only current model-selected pixels',async t=>{
  const f=fixture(t);f.control.dynamicImages=true;f.init()
  const args={detail:{left:10,top:20,width:32,height:16}}
  const result=await f.tool('vm_calc_observe').execute(args,f.exec)
  assert.deepEqual(f.calls[0].args,{}) // Crop is not a new GUI operation.
  const blocks=f.tool('vm_calc_observe').output.render({},result)
  assert.equal(blocks.length,3);assert.equal(blocks[2].attachment.width,64)
  const stream=f.handlers.get('llm/stream')
  const options={...f.route,tools:f.registered,messages:[{content:blocks}]}
  for await(const _ of stream(options,async function*(){yield 'ok'})){}
  await assert.rejects(async()=>{for await(const _ of stream({...options,messages:[{content:blocks.slice(0,2)}]},async function*(){yield 'bad'})){}},/images denied/)
  const receipt=JSON.parse(readFileSync(join(f.root,'calc-detail-1.json'),'utf8'))
  assert.equal(receipt.snapshotId,'s00000001');assert.deepEqual(receipt.geometry,{...args.detail,scale:2})
  await f.tool('vm_calc_select').execute({snapshot_id:'s00000001',detail_x:30,detail_y:20},f.exec)
  assert.deepEqual(f.calls[1].args,{snapshot_id:'s00000001',x:25,y:30})
  assert.equal(f.control.concluded,true)
})

for(const fault of ['missing','newImage','outside','mixed','stale','badCrop','attachmentSize']) {
  test('detail mapping refuses unsafe state '+fault,async t=>{
    const f=fixture(t);f.control.dynamicImages=fault!=='attachmentSize';f.init()
    if(fault==='badCrop' || fault==='attachmentSize'){
      await assert.rejects(f.tool('vm_calc_observe').execute({detail:{left:0,top:0,width:fault==='badCrop'?999:32,height:16}},f.exec))
    }else{
      await f.tool('vm_calc_observe').execute(fault==='missing'?{}:{detail:{left:10,top:20,width:32,height:16}},f.exec)
      let snapshot='s00000001'
      if(fault==='newImage'){
        f.control.reply=(_b:any,{common,state,png}:any)=>({...common,used:2,state:state('s00000002'),png:png.toString('base64')})
        await f.tool('vm_calc_observe').execute({},f.exec);snapshot='s00000002'
      }
      const args:any={snapshot_id:fault==='stale'?'old':snapshot,detail_x:fault==='outside'?64:20,detail_y:10}
      if(fault==='mixed')args.x=25
      await assert.rejects(f.tool('vm_calc_select').execute(args,f.exec))
    }
    assert.equal(f.calls.at(-1).op,'stop')
    assert.equal(f.calls.filter(c=>c.op==='select_cell').length,0)
  })
}

for(const fault of ['unoffered','false','mixed','fallback','raw','stale','repeat','newObservation']) {
  test('cancellation boundary stops without replay '+fault,async t=>{
    const f=fixture(t);f.init()
    await f.tool('vm_calc_observe').execute({},f.exec)
    if(fault!=='unoffered'){
      f.control.reply=(_b:any,{common}:any)=>({...common,used:1,status:'NEEDS_EDIT_CANCEL',snapshot_id:'s00000001'})
      await f.tool('vm_calc_select').execute({snapshot_id:'s00000001'},f.exec)
    }
    f.control.reply=(_b:any,{common,state,png}:any)=>({...common,used:fault==='raw'?2:3,status:'EDIT_CANCEL_ATTEMPT_OBSERVED',
      state:state(fault==='stale'?'s00000001':'s00000002'),png:png.toString('base64')})
    if(fault==='fallback')f.control.reply=(_b:any,{common}:any)=>({...common,used:1,status:'NEEDS_SCREENSHOT_POINT',snapshot_id:'s00000001'})
    let args:any={snapshot_id:'s00000001',cancel_edit:true}
    if(fault==='false')args.cancel_edit=false
    if(fault==='mixed')args={...args,x:25,y:30}
    if(fault==='repeat'){
      await f.tool('vm_calc_select').execute(args,f.exec)
      args.snapshot_id='s00000002'
    }
    if(fault==='newObservation'){
      f.control.reply=(_b:any,{common,state,png}:any)=>({...common,used:2,state:state('s00000002'),png:png.toString('base64')})
      await f.tool('vm_calc_observe').execute({},f.exec);args.snapshot_id='s00000002'
    }
    await assert.rejects(f.tool('vm_calc_select').execute(args,f.exec))
    assert.equal(f.calls.at(-1).op,'stop')
    const count=f.calls.length
    await assert.rejects(f.tool('vm_calc_select').execute(args,f.exec))
    assert.equal(f.calls.length,count)
  })
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

test('first pre-step has no request header; resolved stream and tool header remain mandatory',async t=>{
  const f=fixture(t);f.init()
  f.exec.agent.session.requestHeader=()=>undefined
  f.exec.agent.options={provider:'default',model:'default',reasoningEffort:'high'}
  let entered=false
  await f.handlers.get('agent/pre-step')({agent:f.exec.agent,signal:f.exec.signal},async()=>{entered=true})
  assert.equal(entered,true)
  await assert.rejects(f.tool('vm_calc_observe').execute({},f.exec),/Flash/)
  assert.equal(f.calls.length,0)
  let streamed=false
  const stream=f.handlers.get('llm/stream')
  const options={...f.route,tools:f.registered,messages:[]}
  for await(const _ of stream(options,async function*(){streamed=true;yield 'ok'})){}
  assert.equal(streamed,true)
  f.exec.agent.session.requestHeader=()=>({config:f.route})
  await f.tool('vm_calc_observe').execute({},f.exec)
  assert.equal(f.calls.length,1)
})

test('first pre-step does not permit wrong resolved model requests or another session',async t=>{
  const f=fixture(t);f.init();f.exec.agent.session.requestHeader=()=>undefined
  const pre=f.handlers.get('agent/pre-step')
  await assert.rejects(pre({agent:{session:{id:'other'}},signal:f.exec.signal},async()=>{}),/unauthorized/)
  const stream=f.handlers.get('llm/stream')
  for(const change of [{reasoningEffort:'high'},{reasoningEffort:undefined},{provider:'other'},{model:'other'}]) {
    let called=false
    await assert.rejects(async()=>{for await(const _ of stream({...f.route,...change,tools:f.registered,messages:[]},async function*(){called=true})){}},/denied/)
    assert.equal(called,false)
  }
  assert.equal(f.calls.length,0)
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
