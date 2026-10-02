/** Reuse bounded, UTF-8/type/path-checked read core without exposing file content. */
import { readWorkspaceFile } from './workspace-read.mjs';
export async function fingerprintWorkspaceText({ workspaceRoot, path }) {
	const value = await readWorkspaceFile({ workspaceRoot, path });
	return { path: value.path, bytes: value.bytes, sha256: value.sha256 };
}
