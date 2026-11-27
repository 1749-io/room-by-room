import { readFileSync } from "node:fs";
import { instance } from "@viz-js/viz";

const graph = readFileSync(process.argv[2], "utf8");
const viz = await instance();
process.stdout.write(viz.renderString(graph, { format: "svg", engine: "dot" }));
