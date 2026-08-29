#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const [input, output, sizeArg] = process.argv.slice(2);
if (!input || !output) {
  process.stderr.write("Usage: render_svg.mjs INPUT.svg OUTPUT.png [long-edge]\n");
  process.exit(2);
}
const vendorPackage = path.resolve(here, "../third_party/geometry-dsl/package.json");
const requireFromVendor = createRequire(vendorPackage);
const { Resvg } = requireFromVendor("@resvg/resvg-js");
const svg = await readFile(input);
const edge = Number(sizeArg || 2200);
if (!Number.isFinite(edge) || edge < 100) throw new Error("long-edge must be >= 100");
const resvg = new Resvg(svg, { background: null, fitTo: { mode: "zoom", value: 1 } });
const info = resvg.render();
const scale = edge / Math.max(info.width, info.height);
const finalResvg = new Resvg(svg, { background: null, fitTo: { mode: "zoom", value: scale } });
await writeFile(output, finalResvg.render().asPng());
process.stdout.write(`PNG: ${output}\n`);
