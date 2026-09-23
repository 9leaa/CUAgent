import { copyFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { createImageProbePng } from "./image-probe.mjs";

const agentDirectory = dirname(fileURLToPath(import.meta.url));
const projectRoot = dirname(agentDirectory);
const validationDirectory = join(projectRoot, ".runtime", "workspace", "a0-validation");

await mkdir(validationDirectory, { recursive: true });
await copyFile(join(agentDirectory, "fixtures", "a0", "sales.csv"), join(validationDirectory, "sales.csv"));
await writeFile(join(validationDirectory, "image-input-probe.png"), createImageProbePng());

console.log(validationDirectory);
