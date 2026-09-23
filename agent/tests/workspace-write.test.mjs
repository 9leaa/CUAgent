import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, readdir, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
	writeWorkspaceFile,
	WORKSPACE_WRITE_MAX_BYTES,
	WorkspaceWriteError,
} from "../workspace-write.mjs";

async function withWorkspace(run) {
	const testRoot = await mkdtemp(join(tmpdir(), "osagent-workspace-write-"));
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
		assert.ok(error instanceof WorkspaceWriteError);
		assert.equal(error.code, code);
		return true;
	});
}

test("creates a new UTF-8 file with verification metadata", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		const result = await writeWorkspaceFile({
			workspaceRoot,
			path: "report.md",
			content: "# Report\n",
		});

		assert.equal(result.status, "created");
		assert.equal(result.bytes, 9);
		assert.match(result.sha256, /^[a-f0-9]{64}$/);
		assert.equal(await readFile(join(workspaceRoot, "report.md"), "utf8"), "# Report\n");
	});
});

test("refuses implicit overwrite and allows explicit overwrite", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "report.txt"), "old", "utf8");

		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "report.txt", content: "new" }),
			"FILE_EXISTS",
		);
		const result = await writeWorkspaceFile({
			workspaceRoot,
			path: "report.txt",
			content: "new",
			overwrite: true,
		});

		assert.equal(result.status, "overwritten");
		assert.equal(await readFile(join(workspaceRoot, "report.txt"), "utf8"), "new");
	});
});

test("rejects absolute and parent paths", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "/tmp/report.md", content: "x" }),
			"ABSOLUTE_PATH_DENIED",
		);
		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "../report.md", content: "x" }),
			"PARENT_PATH_DENIED",
		);
	});
});

test("rejects disallowed extensions and oversized content", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "script.sh", content: "echo unsafe" }),
			"FILE_TYPE_DENIED",
		);
		await expectCode(
			writeWorkspaceFile({
				workspaceRoot,
				path: "large.txt",
				content: "x".repeat(WORKSPACE_WRITE_MAX_BYTES + 1),
			}),
			"CONTENT_TOO_LARGE",
		);
		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "binary.txt", content: "a\0b" }),
			"BINARY_CONTENT_DENIED",
		);
	});
});

test("rejects missing parents and final symbolic links", async () => {
	await withWorkspace(async ({ testRoot, workspaceRoot }) => {
		const outside = join(testRoot, "outside.txt");
		await writeFile(outside, "outside", "utf8");
		await symlink(outside, join(workspaceRoot, "link.txt"));

		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "missing/report.md", content: "x" }),
			"NOT_FOUND",
		);
		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "link.txt", content: "x", overwrite: true }),
			"SYMLINK_WRITE_DENIED",
		);
		assert.equal(await readFile(outside, "utf8"), "outside");
	});
});

test("rejects a parent symlink that escapes the workspace", async () => {
	await withWorkspace(async ({ testRoot, workspaceRoot }) => {
		const outside = join(testRoot, "outside");
		await mkdir(outside);
		await symlink(outside, join(workspaceRoot, "escape"));

		await expectCode(
			writeWorkspaceFile({ workspaceRoot, path: "escape/report.md", content: "x" }),
			"SYMLINK_ESCAPE_DENIED",
		);
	});
});

test("concurrent create attempts do not silently overwrite", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		const attempts = await Promise.allSettled([
			writeWorkspaceFile({ workspaceRoot, path: "race.json", content: "one" }),
			writeWorkspaceFile({ workspaceRoot, path: "race.json", content: "two" }),
		]);

		assert.equal(attempts.filter((item) => item.status === "fulfilled").length, 1);
		assert.equal(attempts.filter((item) => item.status === "rejected").length, 1);
		assert.match(await readFile(join(workspaceRoot, "race.json"), "utf8"), /^(one|two)$/);
		assert.equal((await readdir(workspaceRoot)).some((name) => name.startsWith(".osagent-tmp-")), false);
	});
});
