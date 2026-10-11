/** Official DSH tool wiring; no model loop, coordinate generator or SSH. */
import { createHash } from 'node:crypto'
import { constants, openSync, closeSync, fstatSync, fsyncSync, writeFileSync, lstatSync, realpathSync } from 'node:fs'
import { dirname, join } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import { AttachmentId } from '@deepseek-ai/dsh-attachment'
import { assertImageCapableRoute } from './image-probe.ts'
import { deriveDetail, originalPoint } from './calc-image-detail.ts'

const BASE_TOOLS = ['vm_calc_observe', 'vm_calc_select', 'vm_calc_stop']
const UUID = '[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'

export function registerCalcTools(ctx: Context, binding: any, configPath: string, auditPath: string): void {
  const inputMode = binding.protocol === 'calc-input-v1'
  const PROTOCOL = inputMode ? 'calc-input-v1' : 'calc-selection-v1'
  const TOOLS = [...BASE_TOOLS,...(inputMode ? ['vm_calc_input','vm_calc_commit'] : [])]
  if (JSON.stringify(Object.keys(binding).sort()) !== JSON.stringify(['url','token','caseId','stage','protocol','runId','sessionId','cell',...(inputMode?['approvedText','approvedKind']:[])].sort())
      || !Object.values(binding).every(value => typeof value === 'string')
      || binding.url !== 'http://192.168.64.3:8766' || !/^[\w-]{43}$/.test(binding.token)
      || binding.caseId !== 'calc_selection' || binding.stage !== 'p7' || binding.protocol !== PROTOCOL
      || !new RegExp('^calc-select-'+UUID+'$').test(binding.runId)
      || !new RegExp('^session-'+UUID+'$').test(binding.sessionId)
      || !/^[A-Z]{1,3}[1-9][0-9]{0,6}$/.test(binding.cell)) throw new Error('Explicit Calc selection binding required')
  if (inputMode && (!binding.approvedText || Buffer.byteLength(binding.approvedText)>256
      || !['text','decimal'].includes(binding.approvedKind))) throw Error('Bound Calc input required')
  const root = dirname(configPath)
  const info = lstatSync(root)
  const configInfo = lstatSync(configPath)
  if (realpathSync(root) !== root || !info.isDirectory() || info.uid !== process.getuid() || info.mode & 0o077
      || !configInfo.isFile() || configInfo.uid !== process.getuid() || configInfo.mode & 0o077 || configInfo.nlink !== 1
      || dirname(auditPath) !== root) throw new Error('Private Calc evidence directory required')
  function record(path: string, value: unknown, exclusive = false) {
    const fd = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_NOFOLLOW
      | (exclusive ? constants.O_EXCL : constants.O_APPEND), 0o600)
    try {
      const stat = fstatSync(fd)
      if (!stat.isFile() || stat.uid !== process.getuid() || stat.mode & 0o077 || stat.nlink !== 1) throw new Error('Private audit required')
      writeFileSync(fd, JSON.stringify(value)+'\n'); fsyncSync(fd)
    } finally { closeSync(fd) }
  }
  ctx.inject(['connection','webServer'], child => {
    record(join(root,'desktop-ready.json'), {url:child.connection.authenticatedUrl(`http://127.0.0.1:${child.webServer.port}`)}, true)
  })
  let stopped = false, busy = false, lastUsed = 0
  let snapshot: string | undefined
  let latestImage: string | undefined
  let latestDetail: any
  let cancelRequested = false, cancelAttempted = false
  let inputPhase = 'selection'
  const images = new Set<string>()
  const watches = new WeakSet<AbortSignal>()
  async function stop() {
    stopped = true
    const response = await fetch(binding.url, { method: 'POST', headers: { Authorization: `Bearer ${binding.token}`, 'Content-Type':'application/json' },
      body: JSON.stringify({op:'stop',args:{},runId:binding.runId,sessionId:binding.sessionId}), signal:AbortSignal.timeout(5000) })
    if (!response.ok || (await response.json()).stopped !== true) throw new Error('Calc stop unconfirmed')
  }
  function watch(signal: AbortSignal) {
    if (watches.has(signal)) return
    watches.add(signal)
    signal.addEventListener('abort', () => { void stop().catch(() => ctx.logger.error('Calc stop delivery unconfirmed')) }, {once:true})
  }
  function admitScope(exec: any) {
    if (stopped || busy || exec.signal.aborted || exec.parent !== undefined || exec.agent?.session.id !== binding.sessionId) throw new Error('Calc session stopped or unauthorized')
    watch(exec.signal)
  }
  function admit(exec: any) {
    admitScope(exec)
    // pre-step precedes request assembly on the first turn. Only a persisted
    // resolved request header proves the route when a tool actually executes.
    const config = exec.agent.session.requestHeader()?.config
    if (config?.provider !== 'deepseek-account' || config?.model !== 'deepseek-flash' || config?.reasoningEffort !== 'off') throw new Error('Calc requires Flash/off')
  }
  ctx.tools.guard(exec => stopped || busy || exec.signal.aborted || exec.parent !== undefined
    || exec.agent?.session.id !== binding.sessionId || !TOOLS.includes(exec.name) ? 'Calc tool not authorized' : undefined)
  ctx.on('agent/pre-step', async ({agent,signal}, next) => { admitScope({agent,signal}); return next() }, {global:true})
  ctx.on('agent/error', () => { void stop().catch(() => {}) }, {global:true})
  ctx.on('llm/stream', async function* (options, next) {
    const names = (options.tools ?? []).map(tool => tool.name).sort()
    const refs = options.messages.flatMap(m => Array.isArray(m.content) ? m.content.filter(b => b.type === 'image').map(b => b.attachment?.attachmentId) : [])
    if (stopped || busy || options.provider !== 'deepseek-account' || options.model !== 'deepseek-flash' || options.reasoningEffort !== 'off'
        || JSON.stringify(names) !== JSON.stringify([...TOOLS].sort()) || refs.some(id => typeof id !== 'string' || !images.has(id))
        || (latestImage !== undefined && !refs.includes(latestImage))
        || (latestDetail && !refs.includes(latestDetail.image.attachmentId))) throw new Error('Calc request route/tools/images denied')
    record(auditPath, {at:new Date().toISOString(),protocol:PROTOCOL,runId:binding.runId,sessionId:binding.sessionId,
      toolNames:names,provider:options.provider,model:options.model,reasoningEffort:options.reasoningEffort,imageAttachmentIds:refs})
    yield* next()
  })
  const output = { schema: {type:'object',additionalProperties:false,required:['result'],properties:{result:{type:'string'},image:{type:'object'},detailImage:{type:'object'}}},
    render: (_args: unknown, value: any) => [{type:'text',text:value.result}, ...(value.image ? [{type:'image',attachment:{...value.image,
      attachmentId:AttachmentId(value.image.attachmentId),name:'vm-calc.png'}}] : []), ...(value.detailImage ? [{type:'image',attachment:{...value.detailImage,
      attachmentId:AttachmentId(value.detailImage.attachmentId),name:'vm-calc-detail.png'}}] : [])] }
  async function execute(op: string, args: any, exec: any) {
    admit(exec)
    // Recheck capability before any VM request, including a selection request.
    busy = true
    try {
      await assertImageCapableRoute(ctx, exec)
      exec.signal.throwIfAborted()
      if (stopped) throw new Error('Calc stopped')
      if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('Calc argument object required')
      const keys = Object.keys(args).sort().join(',')
      if (op === 'input_cell' || op === 'commit_cell') {
        if (!inputMode || args.snapshot_id!==snapshot || typeof snapshot!=='string'
            || (op==='input_cell' ? keys!=='kind,snapshot_id,text' || inputPhase!=='selected'
              || args.text!==binding.approvedText || args.kind!==binding.approvedKind
              : keys!=='snapshot_id' || inputPhase!=='input')) throw Error('Bound input phase and payload required')
      } else if (op === 'observe' ? !['','detail'].includes(keys) : !['snapshot_id','snapshot_id,x,y','cancel_edit,snapshot_id','detail_x,detail_y,snapshot_id'].includes(keys)
          || typeof args.snapshot_id !== 'string' || args.snapshot_id !== snapshot || ('x' in args && (!Number.isFinite(args.x) || !Number.isFinite(args.y)))) throw new Error('Calc same-snapshot arguments required')
      let dispatchedArgs=op==='observe'?{}:args
      if ('detail_x' in args) {
        if (!latestDetail || latestDetail.snapshotId!==snapshot) throw new Error('Calc current detail required')
        dispatchedArgs={snapshot_id:snapshot,...originalPoint(latestDetail.geometry,args.detail_x,args.detail_y)}
      }
      if ('cancel_edit' in args && (args.cancel_edit !== true || !cancelRequested || cancelAttempted)) throw new Error('Calc cancellation not offered or already attempted')
      if (op === 'select_cell' && cancelRequested && args.cancel_edit !== true) throw new Error('Calc edit requires explicit cancellation')
      if (args.cancel_edit === true) { cancelAttempted=true; cancelRequested=false }
      const response = await fetch(binding.url, {method:'POST',headers:{Authorization:`Bearer ${binding.token}`,'Content-Type':'application/json'},
        body:JSON.stringify({op,args:dispatchedArgs,runId:binding.runId,sessionId:binding.sessionId}), signal:AbortSignal.any([exec.signal,AbortSignal.timeout(40000)])})
      const value = await response.json()
      if (stopped || exec.signal.aborted || !response.ok || value?.protocol !== PROTOCOL || value.runId !== binding.runId
          || value.sessionId !== binding.sessionId || value.cell !== binding.cell || value.inputPermitted !== false
          || value.businessStatus !== 'UNVERIFIED' || !Number.isInteger(value.used) || value.used < lastUsed || value.used > 30) throw new Error('Calc response unconfirmed')
      const status = op === 'observe' ? 'OBSERVED' : value.status
      const allowed = op==='observe'?['OBSERVED']:op==='input_cell'?['INPUT_OBSERVED']:op==='commit_cell'?['COMMIT_ATTEMPT_OBSERVED']
        :['NEEDS_SCREENSHOT_POINT','NEEDS_EDIT_CANCEL','EDIT_CANCEL_ATTEMPT_OBSERVED','SELECTION_OBSERVED']
      if (!allowed.includes(status)) throw new Error('Calc status denied')
      if (status === 'NEEDS_SCREENSHOT_POINT' || status === 'NEEDS_EDIT_CANCEL') {
        if (args.cancel_edit === true) throw new Error('Calc cancellation response mismatch')
        if (value.used !== lastUsed || value.snapshot_id !== snapshot || value.png !== undefined || value.state !== undefined) throw new Error('Calc fallback binding denied')
        if (status === 'NEEDS_EDIT_CANCEL') {
          if (cancelAttempted || 'x' in dispatchedArgs || args.cancel_edit === true) throw new Error('Calc repeated edit cancellation denied')
          cancelRequested=true
        }
        return {result:JSON.stringify({status,cell:binding.cell,snapshot_id:snapshot,used:lastUsed,inputPermitted:false})}
      }
      const alreadySelected = value.selectionRoute === 'already-selected'
      if (alreadySelected && (!inputMode || status!=='SELECTION_OBSERVED' || keys!=='snapshot_id')) throw Error('Calc readonly selection route denied')
      if (value.selectionRoute!==undefined && !alreadySelected) throw Error('Unknown Calc selection route')
      if (value.used <= lastUsed || (['SELECTION_OBSERVED','EDIT_CANCEL_ATTEMPT_OBSERVED','INPUT_OBSERVED','COMMIT_ATTEMPT_OBSERVED'].includes(status) && value.used !== lastUsed+(alreadySelected?1:2))) throw new Error('Calc raw accounting mismatch')
      if ((status === 'EDIT_CANCEL_ATTEMPT_OBSERVED') !== (args.cancel_edit === true)) throw new Error('Calc cancellation response mismatch')
      const state = value.state
      if (!state || typeof state.snapshot_id !== 'string' || !/^s[0-9a-f]{8}$/.test(state.snapshot_id)
          || state.snapshot_id === snapshot || state.app_name !== 'LibreOffice' || state.screenshot_frame_valid !== true
          || typeof value.png !== 'string' || value.png.length > 12*1024*1024) throw new Error('Calc screenshot missing or stale')
      const png = Buffer.from(value.png,'base64')
      if (png.toString('base64') !== value.png || png.length < 33 || png.length > 8*1024*1024
          || !png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))
          || png.readUInt32BE(16) !== state.screenshot_width || png.readUInt32BE(20) !== state.screenshot_height) throw new Error('Calc PNG mismatch')
      if (status === 'SELECTION_OBSERVED' && (value.confirmation?.status !== status || value.confirmation.cell !== binding.cell
          || value.confirmation.snapshot_id !== state.snapshot_id || value.confirmation.inputPermitted !== false)) throw new Error('Calc selection proof missing')
      if (status==='INPUT_OBSERVED' && (value.confirmation?.status!==status || value.confirmation.cell!==binding.cell
          || value.confirmation.snapshot_id!==state.snapshot_id || value.confirmation.text!==binding.approvedText
          || value.confirmation.kind!==binding.approvedKind || value.confirmation.inputEffectVerified!==true
          || value.confirmation.storageTypeVerified!==false || value.confirmation.commitPermitted!==false)) throw Error('Calc input proof missing')
      if (status==='COMMIT_ATTEMPT_OBSERVED' && (value.commitEffectVerified!==false
          || value.storageTypeVerified!==false || value.commitPermitted!==false)) throw Error('Calc commit evidence boundary missing')
      const image = await ctx.get('attachments')!.saveImage({data:new Uint8Array(png),mediaType:'image/png',name:'vm-calc.png'})
      if (!/^sha256:[0-9a-f]{64}$/.test(image.attachmentId) || !['image/png','image/webp'].includes(image.mediaType)
          || ![image.bytes,image.width,image.height].every(v => Number.isInteger(v) && v>0)
          || image.width !== state.screenshot_width || image.height !== state.screenshot_height) throw new Error('Calc attachment unavailable')
      exec.signal.throwIfAborted()
      if (stopped) throw new Error('Calc stopped')
      const ref = {attachmentId:image.attachmentId,mediaType:image.mediaType,bytes:image.bytes,width:image.width,height:image.height}
      let detail:any
      if (op==='observe' && 'detail' in args) {
        const derived=await deriveDetail(png,args.detail,state.screenshot_width,state.screenshot_height)
        const crop=await ctx.get('attachments')!.saveImage({data:new Uint8Array(derived.bytes),mediaType:'image/png',name:'vm-calc-detail.png'})
        if (!/^sha256:[0-9a-f]{64}$/.test(crop.attachmentId) || !['image/png','image/webp'].includes(crop.mediaType)
            || !Number.isSafeInteger(crop.bytes) || crop.bytes<=0 || crop.width!==derived.geometry.width*2
            || crop.height!==derived.geometry.height*2) throw Error('Calc detail attachment mismatch')
        detail={snapshotId:state.snapshot_id,geometry:derived.geometry,sourceSha256:derived.sourceSha256,sha256:derived.sha256,
          image:{attachmentId:crop.attachmentId,mediaType:crop.mediaType,bytes:crop.bytes,width:crop.width,height:crop.height}}
        record(join(root,`calc-detail-${value.used}.json`),detail,true)
        images.add(crop.attachmentId)
      }
      exec.signal.throwIfAborted()
      if (stopped) throw Error('Calc stopped')
      record(join(root,`calc-image-${value.used}.json`), {protocol:PROTOCOL,runId:binding.runId,sessionId:binding.sessionId,
        snapshotId:state.snapshot_id,used:value.used,sourceSha256:createHash('sha256').update(png).digest('hex'),attachment:ref}, true)
      images.add(image.attachmentId); latestImage=image.attachmentId; snapshot=state.snapshot_id; lastUsed=value.used
      latestDetail=detail
      cancelRequested=false // Any new image invalidates the previous cancellation offer.
      const result = {result:JSON.stringify({status,cell:binding.cell,snapshot_id:snapshot,used:lastUsed,
        screenshot_width:state.screenshot_width,screenshot_height:state.screenshot_height,elements_complete:state.elements_complete,
        inputPermitted:false,businessStatus:'UNVERIFIED',...(detail?{detail:{...detail.geometry,coordinateSpace:'detail_pixels',originalMapping:'x=left+detail_x/2,y=top+detail_y/2'}}:{})}),image:ref,...(detail?{detailImage:detail.image}:{})}
      if (status==='SELECTION_OBSERVED') inputPhase='selected'
      if (status==='INPUT_OBSERVED') inputPhase='input'
      if ((status === 'SELECTION_OBSERVED' && !inputMode) || status==='COMMIT_ATTEMPT_OBSERVED') { stopped=true; exec.concludeTurn() }
      return result
    } catch (error) {
      await stop().catch(() => ctx.logger.error('Calc stop delivery unconfirmed; no replay'))
      throw error
    } finally { busy=false }
  }
  ctx.tools.register({name:'vm_calc_observe',description:'Observe the approved VM Calc target. Returns the fresh original screenshot. For dense small rows, request detail:{left,top,width,height} in original pixels covering row/column headers and neighboring cells: this takes a NEW observation and also returns a 2x nearest-neighbor detail of that same image. Read actual row labels and boundaries, not assumed row spacing. Use the new snapshot and detail_x/detail_y for a point in the enlarged image, or x/y in the original. No typing or saving.',
    parameters:{type:'object',properties:{detail:{type:'object',additionalProperties:false,required:['left','top','width','height'],properties:{left:{type:'integer',minimum:0},top:{type:'integer',minimum:0},width:{type:'integer',minimum:16},height:{type:'integer',minimum:16}}}},additionalProperties:false},output,isConcurrencySafe:()=>false,
    execute:(args,exec)=>execute('observe',args,exec)})
  ctx.tools.register({name:'vm_calc_select',description:'Select the bound target cell once. First pass only snapshot_id: the VM uses reliable AX or returns NEEDS_SCREENSHOT_POINT. Then inspect that image yourself and pass its snapshot_id and x,y in original pixels. If the VM instead returns NEEDS_EDIT_CANCEL, and only then, pass the same snapshot_id and cancel_edit:true (no coordinates) to cancel the explicitly approved disposable test input once. Inspect the new EDIT_CANCEL_ATTEMPT_OBSERVED image, then start selection again with only its new snapshot_id. Cancellation observation is not proof of success. The VM clicks once per distinct approved action, observes again and independently checks the selected address. Never retry failed/unknown actions. Selection confirmation ends selection-only mode. In explicit input mode continue with the approved input tool. Neither is business completion.',
    parameters:{type:'object',additionalProperties:false,required:['snapshot_id'],properties:{snapshot_id:{type:'string'},x:{type:'number'},y:{type:'number'},detail_x:{type:'number'},detail_y:{type:'number'},cancel_edit:{type:'boolean',enum:[true]}}},
    output,isConcurrencySafe:()=>false,execute:(args,exec)=>execute('select_cell',args,exec)})
  ctx.tools.register({name:'vm_calc_stop',description:'Stop this original VM selection task without further actions.',
    parameters:{type:'object',properties:{},additionalProperties:false},output,isConcurrencySafe:()=>false,
    async execute(args,exec) { admit(exec); if (!args || Object.keys(args).length) throw new Error('No stop arguments'); await stop(); exec.concludeTurn(); return {result:JSON.stringify({stopped:true,businessStatus:'UNVERIFIED'})} }})
  if (inputMode) {
    // Selection is non-terminal only in this explicitly bound protocol.
    // The input tool description states the next allowed step independently.
    ctx.tools.register({name:'vm_calc_input',description:'After confirmed selection, input only the approved literal once. Inspect the returned new image; independent edit evidence is not saved business success. Never retry failed input.',
      parameters:{type:'object',additionalProperties:false,required:['snapshot_id','text','kind'],properties:{snapshot_id:{type:'string'},text:{type:'string',enum:[binding.approvedText]},kind:{type:'string',enum:[binding.approvedKind]}}},
      output,isConcurrencySafe:()=>false,execute:(args,exec)=>execute('input_cell',args,exec)})
    ctx.tools.register({name:'vm_calc_commit',description:'After INPUT_OBSERVED, confirm one Accept action using that snapshot. Returns a new image and ends this probe; commit effect, storage type and saved workbook remain unverified.',
      parameters:{type:'object',additionalProperties:false,required:['snapshot_id'],properties:{snapshot_id:{type:'string'}}},
      output,isConcurrencySafe:()=>false,execute:(args,exec)=>execute('commit_cell',args,exec)})
  }
  record(join(root,'vm-tools-ready.json'), {protocol:PROTOCOL,runId:binding.runId,sessionId:binding.sessionId,toolNames:[...TOOLS].sort(),
    ...(inputMode?{approvedText:binding.approvedText,approvedKind:binding.approvedKind}:{})}, true)
}
