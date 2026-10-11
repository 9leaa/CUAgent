/** Official DSH tool wiring; no model loop, coordinate generator or SSH. */
import { createHash } from 'node:crypto'
import { constants, openSync, closeSync, fstatSync, fsyncSync, writeFileSync, lstatSync, realpathSync } from 'node:fs'
import { dirname, join } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import { AttachmentId } from '@deepseek-ai/dsh-attachment'
import { assertImageCapableRoute } from './image-probe.ts'

const TOOLS = ['vm_calc_observe', 'vm_calc_select', 'vm_calc_stop']
const PROTOCOL = 'calc-selection-v1'
const UUID = '[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'

export function registerCalcTools(ctx: Context, binding: any, configPath: string, auditPath: string): void {
  if (JSON.stringify(Object.keys(binding).sort()) !== JSON.stringify(['url','token','caseId','stage','protocol','runId','sessionId','cell'].sort())
      || !Object.values(binding).every(value => typeof value === 'string')
      || binding.url !== 'http://192.168.64.3:8766' || !/^[\w-]{43}$/.test(binding.token)
      || binding.caseId !== 'calc_selection' || binding.stage !== 'p7' || binding.protocol !== PROTOCOL
      || !new RegExp('^calc-select-'+UUID+'$').test(binding.runId)
      || !new RegExp('^session-'+UUID+'$').test(binding.sessionId)
      || !/^[A-Z]{1,3}[1-9][0-9]{0,6}$/.test(binding.cell)) throw new Error('Explicit Calc selection binding required')
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
  function admit(exec: any) {
    if (stopped || busy || exec.signal.aborted || exec.parent !== undefined || exec.agent?.session.id !== binding.sessionId) throw new Error('Calc session stopped or unauthorized')
    const config = exec.agent.session.requestHeader()?.config ?? exec.agent.options
    if (config?.provider !== 'deepseek-account' || config?.model !== 'deepseek-flash' || config?.reasoningEffort !== 'off') throw new Error('Calc requires Flash/off')
    watch(exec.signal)
  }
  ctx.tools.guard(exec => stopped || busy || exec.signal.aborted || exec.parent !== undefined
    || exec.agent?.session.id !== binding.sessionId || !TOOLS.includes(exec.name) ? 'Calc tool not authorized' : undefined)
  ctx.on('agent/pre-step', async ({agent,signal}, next) => { admit({agent,signal}); return next() }, {global:true})
  ctx.on('agent/error', () => { void stop().catch(() => {}) }, {global:true})
  ctx.on('llm/stream', async function* (options, next) {
    const names = (options.tools ?? []).map(tool => tool.name).sort()
    const refs = options.messages.flatMap(m => Array.isArray(m.content) ? m.content.filter(b => b.type === 'image').map(b => b.attachment?.attachmentId) : [])
    if (stopped || busy || options.provider !== 'deepseek-account' || options.model !== 'deepseek-flash' || options.reasoningEffort !== 'off'
        || JSON.stringify(names) !== JSON.stringify([...TOOLS].sort()) || refs.some(id => typeof id !== 'string' || !images.has(id))
        || (latestImage !== undefined && !refs.includes(latestImage))) throw new Error('Calc request route/tools/images denied')
    record(auditPath, {at:new Date().toISOString(),protocol:PROTOCOL,runId:binding.runId,sessionId:binding.sessionId,
      toolNames:names,provider:options.provider,model:options.model,reasoningEffort:options.reasoningEffort,imageAttachmentIds:refs})
    yield* next()
  })
  const output = { schema: {type:'object',additionalProperties:false,required:['result'],properties:{result:{type:'string'},image:{type:'object'}}},
    render: (_args: unknown, value: any) => [{type:'text',text:value.result}, ...(value.image ? [{type:'image',attachment:{...value.image,
      attachmentId:AttachmentId(value.image.attachmentId),name:'vm-calc.png'}}] : [])] }
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
      if (op === 'observe' ? keys !== '' : !['snapshot_id','snapshot_id,x,y'].includes(keys)
          || typeof args.snapshot_id !== 'string' || args.snapshot_id !== snapshot || ('x' in args && (!Number.isFinite(args.x) || !Number.isFinite(args.y)))) throw new Error('Calc same-snapshot arguments required')
      const response = await fetch(binding.url, {method:'POST',headers:{Authorization:`Bearer ${binding.token}`,'Content-Type':'application/json'},
        body:JSON.stringify({op,args,runId:binding.runId,sessionId:binding.sessionId}), signal:AbortSignal.any([exec.signal,AbortSignal.timeout(40000)])})
      const value = await response.json()
      if (stopped || exec.signal.aborted || !response.ok || value?.protocol !== PROTOCOL || value.runId !== binding.runId
          || value.sessionId !== binding.sessionId || value.cell !== binding.cell || value.inputPermitted !== false
          || value.businessStatus !== 'UNVERIFIED' || !Number.isInteger(value.used) || value.used < lastUsed || value.used > 30) throw new Error('Calc response unconfirmed')
      const status = op === 'observe' ? 'OBSERVED' : value.status
      if (!['OBSERVED','NEEDS_SCREENSHOT_POINT','SELECTION_OBSERVED'].includes(status)) throw new Error('Calc status denied')
      if (status === 'NEEDS_SCREENSHOT_POINT') {
        if (value.used !== lastUsed || value.snapshot_id !== snapshot || value.png !== undefined || value.state !== undefined) throw new Error('Calc fallback binding denied')
        return {result:JSON.stringify({status,cell:binding.cell,snapshot_id:snapshot,used:lastUsed,inputPermitted:false})}
      }
      if (value.used <= lastUsed || (status === 'SELECTION_OBSERVED' && value.used !== lastUsed+2)) throw new Error('Calc raw accounting mismatch')
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
      const image = await ctx.get('attachments')!.saveImage({data:new Uint8Array(png),mediaType:'image/png',name:'vm-calc.png'})
      if (!/^sha256:[0-9a-f]{64}$/.test(image.attachmentId) || !['image/png','image/webp'].includes(image.mediaType)
          || ![image.bytes,image.width,image.height].every(v => Number.isInteger(v) && v>0)
          || image.width !== state.screenshot_width || image.height !== state.screenshot_height) throw new Error('Calc attachment unavailable')
      exec.signal.throwIfAborted()
      if (stopped) throw new Error('Calc stopped')
      const ref = {attachmentId:image.attachmentId,mediaType:image.mediaType,bytes:image.bytes,width:image.width,height:image.height}
      record(join(root,`calc-image-${value.used}.json`), {protocol:PROTOCOL,runId:binding.runId,sessionId:binding.sessionId,
        snapshotId:state.snapshot_id,used:value.used,sourceSha256:createHash('sha256').update(png).digest('hex'),attachment:ref}, true)
      images.add(image.attachmentId); latestImage=image.attachmentId; snapshot=state.snapshot_id; lastUsed=value.used
      const result = {result:JSON.stringify({status,cell:binding.cell,snapshot_id:snapshot,used:lastUsed,
        screenshot_width:state.screenshot_width,screenshot_height:state.screenshot_height,elements_complete:state.elements_complete,
        inputPermitted:false,businessStatus:'UNVERIFIED'}),image:ref}
      if (status === 'SELECTION_OBSERVED') { stopped=true; exec.concludeTurn() }
      return result
    } catch (error) {
      await stop().catch(() => ctx.logger.error('Calc stop delivery unconfirmed; no replay'))
      throw error
    } finally { busy=false }
  }
  ctx.tools.register({name:'vm_calc_observe',description:'Observe the approved VM Calc target. Returns the fresh screenshot as an image. Read its pixels; do not infer coordinates from old images. No typing or saving.',
    parameters:{type:'object',properties:{},additionalProperties:false},output,isConcurrencySafe:()=>false,
    execute:(args,exec)=>execute('observe',args,exec)})
  ctx.tools.register({name:'vm_calc_select',description:'Select the bound target cell once. First pass only snapshot_id: the VM uses unique reliable AX or returns NEEDS_SCREENSHOT_POINT. In that case inspect the returned observation image yourself and pass its snapshot_id and x,y in original screenshot pixels. The VM clicks once, observes again and independently checks the selected address. Do not retry failed/unknown clicks. Confirmation ends this diagnostic turn; it is not business completion.',
    parameters:{type:'object',additionalProperties:false,required:['snapshot_id'],properties:{snapshot_id:{type:'string'},x:{type:'number'},y:{type:'number'}}},
    output,isConcurrencySafe:()=>false,execute:(args,exec)=>execute('select_cell',args,exec)})
  ctx.tools.register({name:'vm_calc_stop',description:'Stop this original VM selection task without further actions.',
    parameters:{type:'object',properties:{},additionalProperties:false},output,isConcurrencySafe:()=>false,
    async execute(args,exec) { admit(exec); if (!args || Object.keys(args).length) throw new Error('No stop arguments'); await stop(); exec.concludeTurn(); return {result:JSON.stringify({stopped:true,businessStatus:'UNVERIFIED'})} }})
  record(join(root,'vm-tools-ready.json'), {protocol:PROTOCOL,runId:binding.runId,sessionId:binding.sessionId,toolNames:[...TOOLS].sort()}, true)
}
