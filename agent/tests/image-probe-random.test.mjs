import assert from "node:assert/strict";
import test from "node:test";

import {
	createImageProbePngFor,
	createRandomImageProbeAssignment,
	IMAGE_PROBE_COLORS,
	IMAGE_PROBE_POSITIONS,
	readImageProbeAssignment,
} from "../image-probe.mjs";

const COLOR_NAMES = Object.keys(IMAGE_PROBE_COLORS);

test("random assignment places all four distinct colours", () => {
	for (let draw = 0; draw < 50; draw += 1) {
		const assignment = createRandomImageProbeAssignment();
		assert.deepEqual(Object.keys(assignment), [...IMAGE_PROBE_POSITIONS]);
		assert.equal(new Set(Object.values(assignment)).size, 4);
		for (const color of Object.values(assignment)) assert.ok(COLOR_NAMES.includes(color));
	}
});

test("random assignment varies across draws and is not the fixed mapping", () => {
	const fixed = {
		"top-left": "red",
		"top-right": "blue",
		"bottom-left": "green",
		"bottom-right": "yellow",
	};
	const seen = new Set();
	for (let draw = 0; draw < 100; draw += 1) seen.add(JSON.stringify(createRandomImageProbeAssignment()));

	// 4! = 24 permutations; 100 draws must show many, and the point of the change
	// is that the fixed mapping is no longer forced.
	assert.ok(seen.size > 5, `expected varied assignments, saw ${seen.size}`);
	assert.ok(seen.size <= 24);
});

test("encoded pixels round-trip the assignment a verifier reads back", () => {
	for (let draw = 0; draw < 25; draw += 1) {
		const assignment = createRandomImageProbeAssignment();
		const decoded = readImageProbeAssignment(createImageProbePngFor(assignment));
		assert.deepEqual(decoded, assignment);
	}
});

test("the encoder honours an explicit assignment, including the fixed mapping", () => {
	const fixed = {
		"top-left": "red",
		"top-right": "blue",
		"bottom-left": "green",
		"bottom-right": "yellow",
	};
	const reversed = {
		"top-left": "yellow",
		"top-right": "green",
		"bottom-left": "blue",
		"bottom-right": "red",
	};
	assert.deepEqual(readImageProbeAssignment(createImageProbePngFor(fixed)), fixed);
	assert.deepEqual(readImageProbeAssignment(createImageProbePngFor(reversed)), reversed);
});

test("the encoder rejects an unknown colour name", () => {
	assert.throws(
		() => createImageProbePngFor({ "top-left": "mauve", "top-right": "blue", "bottom-left": "green", "bottom-right": "yellow" }),
		/unsupported colour/,
	);
});
