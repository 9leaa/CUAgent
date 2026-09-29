/**
 * Harness adapter — `workspace_image_probe`, the tool-image return path.
 *
 * The framework-agnostic core (`../image-probe.mjs`) draws a fresh random
 * assignment of four colours into the four quadrants and encodes a 96x64 PNG.
 * This adapter commits those bytes to the attachment store and returns them to
 * the model as a real image content block, so the returned image is the thing
 * the model observes — returning a local path is not success.
 *
 * Answer containment: the position→colour mapping is the answer to the probe
 * task, so it never appears in the model-facing value or content. The tool
 * result carries only neutral facts (media type, dimensions, byte size, digest).
 * The answer is appended to a verifier record under `$DSH_HOME/probe-answers/`,
 * which the verification program reads and the model is never shown.
 *
 * The tool is pure with respect to the outside world apart from that verifier
 * record: it invents its bytes in process, and uses no network or shell.
 */
import { createHash } from 'node:crypto'
import { appendFile, mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import { AttachmentError, AttachmentId } from '@deepseek-ai/dsh-attachment'
import type { ImageAttachmentRef, ImageMediaType } from '@deepseek-ai/dsh-attachment'
import type { ContentBlock } from '@deepseek-ai/dsh-llm'
import { defineTool } from '@deepseek-ai/dsh-tools'
import type { GenericCallView, ToolExecution } from '@deepseek-ai/dsh-tools'

import {
  createImageProbePngFor,
  createRandomImageProbeAssignment,
  IMAGE_PROBE_HEIGHT,
  IMAGE_PROBE_WIDTH,
} from '../image-probe.mjs'

export const name = 'workspace-image-probe'

export const inject = ['tools', 'attachments']

const PROBE_WIDTH = IMAGE_PROBE_WIDTH
const PROBE_HEIGHT = IMAGE_PROBE_HEIGHT

const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a] as const

/**
 * Refuse when the calling route cannot actually observe an image result. An
 * image-returning tool is useful only when the exact resolved route declares
 * image input, so an unknown capability refuses instead of failing later.
 */
export async function assertImageCapableRoute(ctx: Context, exec: ToolExecution): Promise<void> {
  const routed = exec.agent?.session.requestHeader()?.config
  const provider = routed?.provider ?? exec.agent?.options.provider
  const model = routed?.model ?? exec.agent?.options.model
  const llm = ctx.get('llm')
  if (provider === undefined || model === undefined || llm === undefined) {
    throw new Error('cannot return the probe image: the current model route could not be resolved')
  }
  const active = await llm.resolveModelInfo(provider, model, exec.signal)
  if (active.inputModalities === undefined || !active.inputModalities.includes('image')) {
    throw new Error(`cannot return the probe image: model "${model}" does not declare image input; switch to an image-capable model`)
  }
}

/**
 * The model-facing value: neutral media facts only. Deliberately carries no
 * colour, no position→colour mapping, and no quadrant ordering, because any of
 * those would hand the model the answer it is being asked to observe.
 */
const PROBE_VALUE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    note: { type: 'string', required: true },
    image: {
      type: 'object',
      additionalProperties: false,
      properties: {
        attachmentId: { type: 'string', required: true },
        mediaType: { type: 'string', required: true },
        bytes: { type: 'integer', required: true },
        width: { type: 'integer', required: true },
        height: { type: 'integer', required: true },
        sha256: { type: 'string', required: true },
      },
    },
  },
} as const

interface ProbeValue {
  note: string
  image: {
    attachmentId: string
    mediaType: ImageMediaType
    bytes: number
    width: number
    height: number
    sha256: string
  }
}

const NEUTRAL_NOTE =
  'Generated a test image. Report what you actually see in it; no answer is included here.'

/** Re-brand the structured outcome into the durable attachment reference an `ImageBlock` carries. */
function imageRefFromValue(image: ProbeValue['image']): ImageAttachmentRef {
  return {
    attachmentId: AttachmentId(image.attachmentId),
    mediaType: image.mediaType,
    bytes: image.bytes,
    width: image.width,
    height: image.height,
    name: 'image-probe.png',
  }
}

/** Project the outcome into model-facing envelope text plus the adjacent image block. */
function probeContent(value: ProbeValue): ContentBlock[] {
  return [
    {
      type: 'text',
      text: `<path>${value.image.attachmentId}</path>
<type>image</type>
<content>
${value.image.mediaType} image, ${value.image.width}x${value.image.height} px, ${value.image.bytes} bytes
</content>`,
    },
    { type: 'image', attachment: imageRefFromValue(value.image) },
  ]
}

/**
 * Resolve the verifier record path. It lives under the harness home rather than
 * the session workspace so the model's own file tools have no reason to reach
 * it, and the verification program reads it from outside the session.
 * @param ctx - plugin context used to read the launch-supplied harness home.
 * @returns the absolute answer-record path and its directory.
 */
function answerRecordLocation(ctx: Context): { directory: string, path: string } {
  const home = ctx.get('profileContext')?.home
    ?? process.env.DSH_HOME
    ?? join(process.cwd(), '.dsh')
  const directory = join(home, 'probe-answers')
  return { directory, path: join(directory, 'answers.jsonl') }
}

export function apply(ctx: Context): void {
  ctx.tools.register(defineTool({
    name: 'workspace_image_probe',
    description:
      'Return a generated test image so you can verify that tool-returned images are actually visible to you. '
      + `The image is ${PROBE_WIDTH}x${PROBE_HEIGHT} px and its four quadrants are coloured independently. `
      + 'Call this tool, then report the colours you actually see, in the order top-left, top-right, bottom-left, '
      + 'bottom-right. This tool returns no answer key: describe the image itself. '
      + 'The tool takes no arguments and uses no network or shell.',
    parameters: {},
    output: {
      schema: PROBE_VALUE_SCHEMA,
      render: (_args, value) => probeContent(value),
    },
    // Each call draws an independent assignment, so concurrent calls cannot conflict.
    isConcurrencySafe: () => true,
    async execute(_args, exec) {
      // Every gate runs before the attachment write, so a refusal never leaves a committed object.
      const attachments = ctx.get('attachments')
      if (attachments === undefined) throw new Error('cannot return the probe image: no attachment service is mounted')
      await assertImageCapableRoute(ctx, exec)

      // A fresh random placement per call: a memorised mapping cannot answer it.
      const assignment = createRandomImageProbeAssignment()
      const png = createImageProbePngFor(assignment)
      if (!PNG_SIGNATURE.every((byte, index) => png[index] === byte)) {
        throw new Error('the probe encoder did not produce a PNG; refusing to commit unknown bytes')
      }
      if (!attachments.imageLimits.mediaTypes.includes('image/png')) {
        throw new Error('cannot return the probe image: this deployment does not accept image/png')
      }
      const sha256 = createHash('sha256').update(png).digest('hex')

      // Persist before returning: the image block must reference a durably
      // committed object by the time the tool/result event is appended.
      let ref: ImageAttachmentRef
      try {
        ref = await attachments.saveImage({
          data: new Uint8Array(png),
          mediaType: 'image/png',
          name: 'image-probe.png',
        })
      } catch (error: unknown) {
        if (error instanceof AttachmentError) {
          throw new Error(`cannot commit the probe image: ${error.code}`, { cause: error })
        }
        throw error
      }

      // Hold the answer out of the model's reach: it goes only to the verifier
      // record, keyed by the digest the model does see, so a verifier can pair
      // one model answer with the exact image it was shown.
      const record = {
        recordedAt: new Date().toISOString(),
        sha256,
        width: ref.width,
        height: ref.height,
        bytes: ref.bytes,
        attachmentId: ref.attachmentId,
        answer: assignment,
      }
      try {
        const { directory, path } = answerRecordLocation(ctx)
        await mkdir(directory, { recursive: true })
        await appendFile(path, `${JSON.stringify(record)}\n`, { mode: 0o600 })
      } catch (error: unknown) {
        throw new Error(
          `cannot record the probe answer for verification: ${error instanceof Error ? error.message : String(error)}`,
          { cause: error },
        )
      }

      return {
        note: NEUTRAL_NOTE,
        image: {
          attachmentId: ref.attachmentId,
          mediaType: ref.mediaType,
          bytes: ref.bytes,
          width: ref.width,
          height: ref.height,
          sha256,
        },
      }
    },
    presentCall(): GenericCallView {
      return { card: 'generic', title: 'Generate the image probe' }
    },
  }))
}
