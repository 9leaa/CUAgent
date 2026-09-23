import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

import {
	assertAllowedExtension,
	resolveExistingWorkspacePath,
	WorkspacePathError,
	workspaceDisplayPath,
} from "./workspace-path.mjs";

export const WORKSPACE_READ_MAX_FILE_BYTES = 1024 * 1024;
export const WORKSPACE_READ_MAX_LINES = 200;
export const WORKSPACE_READ_MAX_OUTPUT_BYTES = 64 * 1024;
export const WORKSPACE_READ_EXTENSIONS = new Set([".txt", ".md", ".csv", ".json"]);

export { WorkspacePathError as WorkspaceReadError };

function positiveInteger(value, fallback, name, maximum) {
	if (value === undefined || value === null) return fallback;
	if (!Number.isInteger(value) || value < 1 || value > maximum) {
		throw new WorkspacePathError("INVALID_RANGE", `${name} must be an integer from 1 to ${maximum}`);
	}
	return value;
}

export async function readWorkspaceFile({ workspaceRoot, path, startLine = 1, maxLines = WORKSPACE_READ_MAX_LINES }) {
	const normalizedStartLine = positiveInteger(startLine, 1, "startLine", Number.MAX_SAFE_INTEGER);
	const normalizedMaxLines = positiveInteger(maxLines, WORKSPACE_READ_MAX_LINES, "maxLines", WORKSPACE_READ_MAX_LINES);
	const { canonicalTarget, requestedPath, targetStat } = await resolveExistingWorkspacePath({
		workspaceRoot,
		path,
		kind: "file",
	});

	assertAllowedExtension(canonicalTarget, WORKSPACE_READ_EXTENSIONS);
	if (targetStat.size > WORKSPACE_READ_MAX_FILE_BYTES) {
		throw new WorkspacePathError("FILE_TOO_LARGE", `file exceeds ${WORKSPACE_READ_MAX_FILE_BYTES} bytes`);
	}

	let buffer;
	try {
		buffer = await readFile(canonicalTarget);
	} catch {
		throw new WorkspacePathError("UNAVAILABLE", `file is unavailable: ${workspaceDisplayPath(requestedPath)}`);
	}
	if (buffer.length > WORKSPACE_READ_MAX_FILE_BYTES) {
		throw new WorkspacePathError("FILE_TOO_LARGE", `file exceeds ${WORKSPACE_READ_MAX_FILE_BYTES} bytes`);
	}

	let text;
	try {
		text = new TextDecoder("utf-8", { fatal: true }).decode(buffer);
	} catch {
		throw new WorkspacePathError("BINARY_FILE_DENIED", "file is not valid UTF-8 text");
	}
	if (text.includes("\0")) {
		throw new WorkspacePathError("BINARY_FILE_DENIED", "file contains null bytes");
	}

	const lines = text.length === 0 ? [] : text.split(/\r\n|\n|\r/);
	if (normalizedStartLine > lines.length + 1) {
		throw new WorkspacePathError("INVALID_RANGE", "startLine is beyond the end of the file");
	}
	const availableLines = lines.slice(normalizedStartLine - 1, normalizedStartLine - 1 + normalizedMaxLines);
	const selectedLines = [];
	let outputBytes = 0;
	for (const line of availableLines) {
		const additionalBytes = Buffer.byteLength(line, "utf8") + (selectedLines.length > 0 ? 1 : 0);
		if (outputBytes + additionalBytes > WORKSPACE_READ_MAX_OUTPUT_BYTES) break;
		selectedLines.push(line);
		outputBytes += additionalBytes;
	}
	if (availableLines.length > 0 && selectedLines.length === 0) {
		throw new WorkspacePathError("OUTPUT_TOO_LARGE", `a single line exceeds ${WORKSPACE_READ_MAX_OUTPUT_BYTES} bytes`);
	}

	const content = selectedLines.join("\n");
	const endLine = selectedLines.length === 0 ? normalizedStartLine - 1 : normalizedStartLine + selectedLines.length - 1;
	return {
		path: workspaceDisplayPath(requestedPath),
		content,
		startLine: normalizedStartLine,
		endLine,
		totalLines: lines.length,
		truncated: endLine < lines.length,
		bytes: buffer.length,
		sha256: createHash("sha256").update(buffer).digest("hex"),
	};
}
