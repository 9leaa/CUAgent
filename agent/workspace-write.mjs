import { createHash, randomUUID } from "node:crypto";
import { link, lstat, open, realpath, rename, unlink } from "node:fs/promises";
import { basename, dirname, join } from "node:path";

import {
	assertAllowedExtension,
	canonicalWorkspaceRoot,
	isInsideWorkspace,
	normalizeWorkspacePath,
	resolveExistingWorkspacePath,
	WorkspacePathError,
	workspaceDisplayPath,
} from "./workspace-path.mjs";

export const WORKSPACE_WRITE_MAX_BYTES = 256 * 1024;
export const WORKSPACE_WRITE_EXTENSIONS = new Set([".txt", ".md", ".json"]);

export { WorkspacePathError as WorkspaceWriteError };

export async function prepareWorkspaceWriteTarget({ workspaceRoot, path }) {
	const requestedPath = normalizeWorkspacePath(path, { defaultPath: null });
	if (requestedPath === ".") {
		throw new WorkspacePathError("INVALID_PATH", "path must name a file");
	}
	assertAllowedExtension(requestedPath, WORKSPACE_WRITE_EXTENSIONS);

	const canonicalRoot = await canonicalWorkspaceRoot(workspaceRoot);
	const parentPath = dirname(requestedPath);
	const { canonicalTarget: canonicalParent } = await resolveExistingWorkspacePath({
		workspaceRoot: canonicalRoot,
		path: parentPath,
		kind: "directory",
	});
	const targetPath = join(canonicalParent, basename(requestedPath));
	if (!isInsideWorkspace(canonicalRoot, targetPath)) {
		throw new WorkspacePathError("PATH_ESCAPE_DENIED", "path resolves outside the workspace");
	}

	return { canonicalRoot, requestedPath, targetPath };
}

async function inspectWriteTarget({ canonicalRoot, requestedPath, targetPath }) {
	let targetInfo;
	try {
		targetInfo = await lstat(targetPath);
	} catch (error) {
		if (error && error.code === "ENOENT") return { exists: false };
		throw new WorkspacePathError("UNAVAILABLE", `file is unavailable: ${workspaceDisplayPath(requestedPath)}`);
	}

	if (targetInfo.isSymbolicLink()) {
		throw new WorkspacePathError("SYMLINK_WRITE_DENIED", "writing through a symbolic link is not allowed");
	}
	if (!targetInfo.isFile()) {
		throw new WorkspacePathError("NOT_A_FILE", `not a regular file: ${workspaceDisplayPath(requestedPath)}`);
	}

	let canonicalTarget;
	try {
		canonicalTarget = await realpath(targetPath);
	} catch {
		throw new WorkspacePathError("UNAVAILABLE", `file is unavailable: ${workspaceDisplayPath(requestedPath)}`);
	}
	if (!isInsideWorkspace(canonicalRoot, canonicalTarget)) {
		throw new WorkspacePathError("PATH_ESCAPE_DENIED", "path resolves outside the workspace");
	}
	return {
		exists: true,
		fingerprint: `${targetInfo.dev}:${targetInfo.ino}:${targetInfo.size}:${targetInfo.mtimeMs}`,
	};
}

export async function writeWorkspaceFile({ workspaceRoot, path, content, overwrite = false }) {
	if (typeof content !== "string") {
		throw new WorkspacePathError("INVALID_CONTENT", "content must be a string");
	}
	if (typeof overwrite !== "boolean") {
		throw new WorkspacePathError("INVALID_OVERWRITE", "overwrite must be a boolean");
	}
	if (content.includes("\0")) {
		throw new WorkspacePathError("BINARY_CONTENT_DENIED", "content contains a null byte");
	}
	const contentBuffer = Buffer.from(content, "utf8");
	if (contentBuffer.length > WORKSPACE_WRITE_MAX_BYTES) {
		throw new WorkspacePathError("CONTENT_TOO_LARGE", `content exceeds ${WORKSPACE_WRITE_MAX_BYTES} bytes`);
	}

	const prepared = await prepareWorkspaceWriteTarget({ workspaceRoot, path });
	const initialState = await inspectWriteTarget(prepared);
	if (initialState.exists && !overwrite) {
		throw new WorkspacePathError("FILE_EXISTS", "file already exists; set overwrite to true to replace it");
	}

	const parentDirectory = dirname(prepared.targetPath);
	const temporaryPath = join(parentDirectory, `.osagent-tmp-${process.pid}-${randomUUID()}`);
	let temporaryHandle;
	let temporaryExists = false;
	try {
		temporaryHandle = await open(temporaryPath, "wx", 0o600);
		temporaryExists = true;
		await temporaryHandle.writeFile(contentBuffer);
		await temporaryHandle.sync();
		await temporaryHandle.close();
		temporaryHandle = undefined;

		const finalState = await inspectWriteTarget(prepared);
		if (
			finalState.exists !== initialState.exists ||
			(finalState.exists && finalState.fingerprint !== initialState.fingerprint)
		) {
			throw new WorkspacePathError("WRITE_CONFLICT", "file changed during the write; retry after reading it");
		}
		if (finalState.exists) {
			if (!overwrite) {
				throw new WorkspacePathError("FILE_EXISTS", "file already exists; set overwrite to true to replace it");
			}
			await rename(temporaryPath, prepared.targetPath);
			temporaryExists = false;
		} else {
			try {
				await link(temporaryPath, prepared.targetPath);
			} catch (error) {
				if (error && error.code === "EEXIST") {
					throw new WorkspacePathError("WRITE_CONFLICT", "file changed during the write; retry after reading it");
				}
				throw error;
			}
			await unlink(temporaryPath);
			temporaryExists = false;
		}
	} catch (error) {
		if (error instanceof WorkspacePathError) throw error;
		throw new WorkspacePathError("WRITE_FAILED", `failed to write: ${workspaceDisplayPath(prepared.requestedPath)}`);
	} finally {
		if (temporaryHandle) await temporaryHandle.close().catch(() => {});
		if (temporaryExists) await unlink(temporaryPath).catch(() => {});
	}

	return {
		path: workspaceDisplayPath(prepared.requestedPath),
		status: initialState.exists ? "overwritten" : "created",
		bytes: contentBuffer.length,
		sha256: createHash("sha256").update(contentBuffer).digest("hex"),
	};
}
