import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const agentDirectory = dirname(fileURLToPath(import.meta.url));
const projectRoot = dirname(agentDirectory);
const validationDirectory = join(projectRoot, ".runtime", "workspace", "a0-validation");
const result = JSON.parse(await readFile(join(validationDirectory, "csv-stats.json"), "utf8"));
const report = await readFile(join(validationDirectory, "csv-report.md"), "utf8");

assert.equal(result.path, "a0-validation/sales.csv");
assert.equal(result.rowCount, 5);
assert.equal(result.columnCount, 3);
assert.deepEqual(result.columns, ["region", "units", "revenue"]);
assert.deepEqual(result.numeric.units, { count: 5, missing: 0, sum: 14, min: 1, max: 5, mean: 2.8 });
assert.deepEqual(result.numeric.revenue, { count: 4, missing: 1, sum: 430, min: 70, max: 150, mean: 107.5 });
for (const expectedText of ["5", "14", "2.8", "430", "107.5"]) {
	assert.ok(report.includes(expectedText), `report is missing independently expected value: ${expectedText}`);
}

console.log("A0 CSV verification passed");
