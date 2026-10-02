/** Keep framework-neutral errors in core; preserve their codes at the official seam. */
import { HarnessError } from '@deepseek-ai/dsh-llm'
import { WorkspacePathError } from '../workspace-path.mjs'
export async function withWorkspaceErrors<T>(run: () => Promise<T>): Promise<T> {
  try { return await run() }
  catch (error) {
    if (error instanceof WorkspacePathError) {
      const wrapped = new HarnessError(error.message, error.code, { cause: error })
      wrapped.name = 'WorkspaceToolError'
      throw wrapped
    }
    throw error
  }
}
