import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
	listWorkspaceDirectory,
	WORKSPACE_LIST_MAX_ENTRIES,
	WorkspaceListError,
} from "../workspace-list.mjs";

async function withWorkspace(run) {
	const testRoot = await mkdtemp(join(tmpdir(), "osagent-workspace-list-"));
	const workspaceRoot = join(testRoot, "workspace");
	await mkdir(workspaceRoot);
	try {
		await run({ testRoot, workspaceRoot });
	} finally {
		await rm(testRoot, { recursive: true, force: true });
	}
}

async function expectCode(promise, code) {
	await assert.rejects(promise, (error) => {
		assert.ok(error instanceof WorkspaceListError);
		assert.equal(error.code, code);
		return true;
	});
}

test("lists root entries in stable order without following symlinks", async () => {
	await withWorkspace(async ({ testRoot, workspaceRoot }) => {
		await mkdir(join(workspaceRoot, "beta"));
		await writeFile(join(workspaceRoot, "alpha.txt"), "alpha", "utf8");
		await symlink(join(testRoot, "outside"), join(workspaceRoot, "outside-link"));

		const result = await listWorkspaceDirectory({ workspaceRoot });

		assert.deepEqual(result, {
			path: ".",
			entries: [
				{ name: "alpha.txt", type: "file" },
				{ name: "beta", type: "directory" },
				{ name: "outside-link", type: "symlink" },
			],
			totalEntries: 3,
			truncated: false,
		});
	});
});

test("lists a nested relative directory and accepts a model @ prefix", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await mkdir(join(workspaceRoot, "nested"));
		await writeFile(join(workspaceRoot, "nested", "item.txt"), "item", "utf8");

		const result = await listWorkspaceDirectory({ workspaceRoot, path: "@nested" });

		assert.equal(result.path, "nested");
		assert.deepEqual(result.entries, [{ name: "item.txt", type: "file" }]);
	});
});

test("rejects absolute and parent paths", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await expectCode(
			listWorkspaceDirectory({ workspaceRoot, path: "/tmp" }),
			"ABSOLUTE_PATH_DENIED",
		);
		await expectCode(
			listWorkspaceDirectory({ workspaceRoot, path: "../outside" }),
			"PARENT_PATH_DENIED",
		);
		await expectCode(
			listWorkspaceDirectory({ workspaceRoot, path: "nested/../outside" }),
			"PARENT_PATH_DENIED",
		);
	});
});

test("rejects a symlink that resolves outside the workspace", async () => {
	await withWorkspace(async ({ testRoot, workspaceRoot }) => {
		const outside = join(testRoot, "outside");
		await mkdir(outside);
		await symlink(outside, join(workspaceRoot, "escape"));

		await expectCode(
			listWorkspaceDirectory({ workspaceRoot, path: "escape" }),
			"SYMLINK_ESCAPE_DENIED",
		);
	});
});

test("allows a symlink that resolves to a directory inside the workspace", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await mkdir(join(workspaceRoot, "real"));
		await writeFile(join(workspaceRoot, "real", "inside.txt"), "inside", "utf8");
		await symlink(join(workspaceRoot, "real"), join(workspaceRoot, "alias"));

		const result = await listWorkspaceDirectory({ workspaceRoot, path: "alias" });

		assert.deepEqual(result.entries, [{ name: "inside.txt", type: "file" }]);
	});
});

test("rejects files and missing directories", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "file.txt"), "content", "utf8");

		await expectCode(
			listWorkspaceDirectory({ workspaceRoot, path: "file.txt" }),
			"NOT_A_DIRECTORY",
		);
		await expectCode(
			listWorkspaceDirectory({ workspaceRoot, path: "missing" }),
			"NOT_FOUND",
		);
	});
});

test("caps large directory results", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await Promise.all(
			Array.from({ length: WORKSPACE_LIST_MAX_ENTRIES + 3 }, (_, index) =>
				writeFile(join(workspaceRoot, `item-${String(index).padStart(3, "0")}.txt`), "", "utf8"),
			),
		);

		const result = await listWorkspaceDirectory({ workspaceRoot });

		assert.equal(result.entries.length, WORKSPACE_LIST_MAX_ENTRIES);
		assert.equal(result.totalEntries, WORKSPACE_LIST_MAX_ENTRIES + 3);
		assert.equal(result.truncated, true);
	});
});
