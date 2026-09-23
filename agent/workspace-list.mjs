import { readdir } from "node:fs/promises";

import {
	resolveExistingWorkspacePath,
	WorkspacePathError,
	workspaceDisplayPath,
} from "./workspace-path.mjs";

export const WORKSPACE_LIST_MAX_ENTRIES = 200;

export { WorkspacePathError as WorkspaceListError };

function entryType(entry) {
	if (entry.isDirectory()) return "directory";
	if (entry.isFile()) return "file";
	if (entry.isSymbolicLink()) return "symlink";
	return "other";
}

export async function listWorkspaceDirectory({ workspaceRoot, path = "." }) {
	const { canonicalTarget, requestedPath } = await resolveExistingWorkspacePath({
		workspaceRoot,
		path,
		kind: "directory",
	});

	let directoryEntries;
	try {
		directoryEntries = await readdir(canonicalTarget, { withFileTypes: true });
	} catch {
		throw new WorkspaceListError("UNAVAILABLE", `directory is unavailable: ${safeDisplayPath(requestedPath)}`);
	}

	directoryEntries.sort((left, right) => {
		if (left.name < right.name) return -1;
		if (left.name > right.name) return 1;
		return 0;
	});

	const entries = directoryEntries.slice(0, WORKSPACE_LIST_MAX_ENTRIES).map((entry) => ({
		name: entry.name,
		type: entryType(entry),
	}));

	return {
		path: workspaceDisplayPath(requestedPath),
		entries,
		totalEntries: directoryEntries.length,
		truncated: directoryEntries.length > WORKSPACE_LIST_MAX_ENTRIES,
	};
}
