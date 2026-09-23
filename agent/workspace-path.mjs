import { realpath, stat } from "node:fs/promises";
import { extname, isAbsolute, normalize, relative, resolve, sep } from "node:path";

export class WorkspacePathError extends Error {
	constructor(code, message) {
		super(message);
		this.name = "WorkspacePathError";
		this.code = code;
	}
}

export function normalizeWorkspacePath(input, { defaultPath = "." } = {}) {
	if (input === undefined || input === null || input === "") {
		if (defaultPath === null) {
			throw new WorkspacePathError("INVALID_PATH", "path is required");
		}
		return defaultPath;
	}
	if (typeof input !== "string") {
		throw new WorkspacePathError("INVALID_PATH", "path must be a string");
	}

	const withoutModelPrefix = input.startsWith("@") ? input.slice(1) : input;
	if (withoutModelPrefix.includes("\0")) {
		throw new WorkspacePathError("INVALID_PATH", "path contains a null byte");
	}
	if (isAbsolute(withoutModelPrefix)) {
		throw new WorkspacePathError("ABSOLUTE_PATH_DENIED", "absolute paths are not allowed");
	}
	if (withoutModelPrefix.split(sep).includes("..")) {
		throw new WorkspacePathError("PARENT_PATH_DENIED", "parent path segments are not allowed");
	}

	const normalized = normalize(withoutModelPrefix || defaultPath || ".");
	if (normalized === ".." || normalized.startsWith(`..${sep}`)) {
		throw new WorkspacePathError("PARENT_PATH_DENIED", "parent path segments are not allowed");
	}
	return normalized;
}

export function workspaceDisplayPath(requestedPath) {
	return requestedPath === "." ? "." : requestedPath.split(sep).join("/");
}

export function isInsideWorkspace(root, candidate) {
	const fromRoot = relative(root, candidate);
	return fromRoot === "" || (!fromRoot.startsWith(`..${sep}`) && fromRoot !== ".." && !isAbsolute(fromRoot));
}

export async function canonicalWorkspaceRoot(workspaceRoot) {
	if (typeof workspaceRoot !== "string" || workspaceRoot.length === 0) {
		throw new WorkspacePathError("INVALID_ROOT", "workspace root is not configured");
	}
	try {
		return await realpath(resolve(workspaceRoot));
	} catch {
		throw new WorkspacePathError("INVALID_ROOT", "workspace root is unavailable");
	}
}

export async function resolveExistingWorkspacePath({ workspaceRoot, path = ".", kind }) {
	const requestedPath = normalizeWorkspacePath(path);
	const canonicalRoot = await canonicalWorkspaceRoot(workspaceRoot);
	let canonicalTarget;
	try {
		canonicalTarget = await realpath(resolve(canonicalRoot, requestedPath));
	} catch (error) {
		if (error && error.code === "ENOENT") {
			throw new WorkspacePathError("NOT_FOUND", `path not found: ${workspaceDisplayPath(requestedPath)}`);
		}
		throw new WorkspacePathError("UNAVAILABLE", `path is unavailable: ${workspaceDisplayPath(requestedPath)}`);
	}

	if (!isInsideWorkspace(canonicalRoot, canonicalTarget)) {
		throw new WorkspacePathError("SYMLINK_ESCAPE_DENIED", "path resolves outside the workspace");
	}

	let targetStat;
	try {
		targetStat = await stat(canonicalTarget);
	} catch {
		throw new WorkspacePathError("UNAVAILABLE", `path is unavailable: ${workspaceDisplayPath(requestedPath)}`);
	}
	if (kind === "directory" && !targetStat.isDirectory()) {
		throw new WorkspacePathError("NOT_A_DIRECTORY", `not a directory: ${workspaceDisplayPath(requestedPath)}`);
	}
	if (kind === "file" && !targetStat.isFile()) {
		throw new WorkspacePathError("NOT_A_FILE", `not a regular file: ${workspaceDisplayPath(requestedPath)}`);
	}

	return { canonicalRoot, canonicalTarget, requestedPath, targetStat };
}

export function assertAllowedExtension(path, allowedExtensions) {
	const extension = extname(path).toLowerCase();
	if (!allowedExtensions.has(extension)) {
		throw new WorkspacePathError("FILE_TYPE_DENIED", "file extension is not allowed");
	}
}
