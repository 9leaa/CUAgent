/**
 * Independent verifier for the `workspace_image_probe` image chain.
 *
 * It deliberately does NOT trust the probe tool's own report. For every probe
 * call in a session it:
 *
 *   1. pairs the `tool/call` with its `tool/result` by call id, so each image is
 *      matched to the model answer that belongs to it;
 *   2. reads the image block's `attachmentId` (a `sha256:` digest) from that
 *      result, and locates the persisted object under the attachment store;
 *   3. re-decodes the stored bytes and samples one interior pixel per quadrant,
 *      so the colours come from the image, not from any tool text;
 *   4. compares the answer recorded by the probe (the answer key) against those
 *      decoded pixels, proving the key describes the image actually shown;
 *   5. compares the model's own answer for that call against the decoded pixels.
 *
 * Model answers are read from the session transcript that follows each probe
 * result, and are matched to the preceding attachment. English and Chinese
 * colour words are both accepted.
 *
 * Usage:
 *   node agent/verify-image-probe.mjs \
 *     --session <session.v4.jsonl.zstd or .jsonl> \
 *     --attachments <$DSH_HOME/attachments/v1/objects> \
 *     --answers <$DSH_HOME/probe-answers/answers.jsonl>
 *
 * Exit code 0 only when every probe call's model answer matches its own image.
 */
import { readFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { inflateSync } from "node:zlib";
import { join } from "node:path";

const WIDTH = 96;
const HEIGHT = 64;
const STRIDE = WIDTH * 4 + 1;

/** Quadrant sample points in the order the reviewer asks the model to report. */
const SAMPLES = [
	["top-left", 10, 10],
	["top-right", 80, 10],
	["bottom-left", 10, 50],
	["bottom-right", 80, 50],
];

const RGB_TO_NAME = new Map([
	["255,0,0", "red"],
	["0,0,255", "blue"],
	["0,255,0", "green"],
	["255,255,0", "yellow"],
]);

/**
 * Colour words accepted in a model answer, English and Chinese.
 *
 * Chinese entries include the bare colour and the common `色`-suffixed form.
 */
const COLOR_WORDS = [
	["red", "red"],
	["红", "red"],
	["红颜色", "red"],
	["blue", "blue"],
	["蓝", "blue"],
	["green", "green"],
	["绿", "green"],
	["yellow", "yellow"],
	["黄", "yellow"],
];

const POSITION_ORDER = ["top-left", "top-right", "bottom-left", "bottom-right"];

function parseArgs(argv) {
	const out = {};
	for (let i = 0; i < argv.length; i += 1) {
		const token = argv[i];
		if (!token.startsWith("--")) continue;
		out[token.slice(2)] = argv[i + 1];
		i += 1;
	}
	return out;
}

/** Read a session log, transparently decompressing zstd when needed. */
function readSessionLines(path) {
	if (!existsSync(path)) throw new Error(`session log not found: ${path}`);
	if (path.endsWith(".zstd")) {
		const text = execFileSync("zstd", ["-dc", path], { maxBuffer: 512 * 1024 * 1024 }).toString("utf8");
		return text.split("\n");
	}
	return readFileSync(path, "utf8").split("\n");
}

/**
 * Locate a persisted attachment object.
 *
 * The store shards by the digest's first two characters into a directory, and
 * the file keeps the COMPLETE digest as its name (not the remainder), e.g.
 * `<root>/44/44cb6149…f974ab`.
 */
function objectPath(root, digest) {
	return join(root, digest.slice(0, 2), digest);
}

/** Decode a probe PNG and read one interior pixel per quadrant. */
function decodeQuadrants(png) {
	const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
	if (!png.subarray(0, 8).equals(signature)) throw new Error("not a PNG");
	const idat = [];
	let offset = 8;
	while (offset < png.length) {
		const length = png.readUInt32BE(offset);
		const type = png.subarray(offset + 4, offset + 8).toString("ascii");
		if (type === "IDAT") idat.push(png.subarray(offset + 8, offset + 8 + length));
		offset += 12 + length;
	}
	const raw = inflateSync(Buffer.concat(idat));
	const result = {};
	for (const [position, x, y] of SAMPLES) {
		const base = y * STRIDE + 1 + x * 4;
		const name = RGB_TO_NAME.get(`${raw[base]},${raw[base + 1]},${raw[base + 2]}`);
		if (name === undefined) throw new Error(`unrecognised colour at ${position}`);
		result[position] = name;
	}
	return result;
}

/**
 * Extract ordered colour mentions from a model answer, accepting English and
 * Chinese words. Position words are ignored: the reviewer fixes the reporting
 * order in the prompt, so the mention order is the quadrant order.
 * @param text - the model's answer text.
 * @returns position name to colour name, for as many positions as were named.
 */
function parseModelAnswer(text) {
	const found = [];
	for (const [word, canonical] of COLOR_WORDS) {
		const pattern = word.length === 1 && /[\u4e00-\u9fff]/u.test(word)
			? new RegExp(word, "gu")
			: new RegExp(`\\b${word}\\b`, "gi");
		let match;
		while ((match = pattern.exec(text)) !== null) found.push([match.index, canonical, match[0]]);
	}
	found.sort((a, b) => a[0] - b[0]);
	const result = {};
	const used = new Set();
	for (const [, canonical] of found) {
		if (used.has(canonical)) continue;
		used.add(canonical);
		if (Object.keys(result).length < POSITION_ORDER.length) {
			result[POSITION_ORDER[Object.keys(result).length]] = canonical;
		}
	}
	return result;
}

const args = parseArgs(process.argv.slice(2));
const sessionPath = args.session;
const attachmentsRoot = args.attachments;
const answersPath = args.answers;

if (!sessionPath || !attachmentsRoot || !answersPath) {
	console.error("usage: --session <log> --attachments <objects dir> --answers <answers.jsonl>");
	process.exit(2);
}

// The answer key: what the probe believed it drew, per image digest.
const keyByDigest = new Map();
if (existsSync(answersPath)) {
	for (const line of readFileSync(answersPath, "utf8").split("\n")) {
		if (line.trim() === "") continue;
		const record = JSON.parse(line);
		keyByDigest.set(record.sha256, record);
	}
}

// Pair each probe tool call with its result, in order.
const lines = readSessionLines(sessionPath);
const calls = new Map();
const probes = [];
const timeline = [];
for (const line of lines) {
	if (line.trim() === "") continue;
	let record;
	try {
		record = JSON.parse(line);
	} catch {
		continue;
	}
	const data = record.data;
	if (record.type === "tool/call" && data?.name === "workspace_image_probe") {
		calls.set(data.callId, { callId: data.callId });
	}
	if (record.type === "tool/result" && data?.message?.toolCallId !== undefined) {
		const call = calls.get(data.message.toolCallId);
		if (call !== undefined) {
			const image = (data.message.content ?? []).find(block => block.type === "image");
			call.image = image?.attachment;
			call.text = (data.message.content ?? []).find(block => block.type === "text")?.text;
			call.resultSeq = record.seq;
		}
	}
	if (record.type === "assistant/message") {
		const text = (data?.message?.content ?? [])
			.filter(block => block.type === "text")
			.map(block => block.text)
			.join("\n");
		if (text.trim() !== "") timeline.push({ seq: record.seq, text });
	}
}

for (const call of calls.values()) if (call.image !== undefined) probes.push(call);

if (probes.length === 0) {
	console.log("no workspace_image_probe calls with an image result found");
	process.exit(2);
}

console.log(`probe calls with images : ${probes.length}`);
console.log(`answer-key records      : ${keyByDigest.size}`);
console.log("");

let allPass = true;
probes.forEach((probe, index) => {
	const attachmentId = probe.image.attachmentId;
	const digest = attachmentId.startsWith("sha256:") ? attachmentId.slice("sha256:".length) : attachmentId;
	const path = objectPath(attachmentsRoot, digest);
	const label = `#${index + 1} call ${probe.callId}`;

	console.log(`${label}`);
	console.log(`  attachment : ${attachmentId.slice(0, 23)}…  ${probe.image.width}x${probe.image.height} ${probe.image.bytes}b`);

	if (!existsSync(path)) {
		console.log(`  FAIL: persisted object missing at ${path}`);
		allPass = false;
		console.log("");
		return;
	}
	const png = readFileSync(path);
	const digestOk = createHash("sha256").update(png).digest("hex") === digest;
	const decoded = decodeQuadrants(png);
	console.log(`  digest ok  : ${digestOk}`);
	console.log(`  pixels     : ${JSON.stringify(decoded)}`);

	const key = keyByDigest.get(digest);
	if (key === undefined) {
		console.log("  key        : (no record for this digest)");
	} else {
		const keyMatches = JSON.stringify(key.answer) === JSON.stringify(decoded);
		console.log(`  key        : ${JSON.stringify(key.answer)}  matches pixels: ${keyMatches}`);
		if (!keyMatches) allPass = false;
	}

	// The model answer for this call is the first assistant text after its result.
	const answerEntry = timeline.find(entry => entry.seq > probe.resultSeq);
	const answerText = (answerEntry?.text ?? "").trim();
	const model = parseModelAnswer(answerText);
	const matches = POSITION_ORDER.every(position => decoded[position] === model[position]);
	console.log(`  model text : ${answerText.replace(/\s+/gu, " ").slice(0, 160)}`);
	console.log(`  model      : ${JSON.stringify(model)}`);
	console.log(`  MATCH      : ${matches ? "yes" : "NO"}`);
	if (!digestOk || !matches) allPass = false;
	console.log("");
});

console.log(allPass ? "RESULT: PASS (every probe answer matches its own image)" : "RESULT: FAIL");
process.exit(allPass ? 0 : 1);
