// node scripts/shots_at.mjs <outdir> t1 t2 ... -> one PNG per time, for checking a change without a full stills pass.
import fs from 'fs'; import path from 'path'; import { root, sync, launch, open } from './lib.mjs';
const out = path.join(root, process.argv[2]); fs.mkdirSync(out, { recursive: true });
sync(); const b = await launch(); const { p, errs } = await open(b);
const info = await p.evaluate(() => ({ D: window.__duration, rows: Math.max(...S.map(s => s.row)) + 1, MS, labels: LB.map(l => [l[0], Math.round(l[2]), Math.round(l[3]), l[5]]) }));
console.log(JSON.stringify(info));
for (const a of process.argv.slice(3)) { const t = +a; await p.evaluate(t => window.__seek(t), t); await p.screenshot({ path: path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`) }); }
await b.close(); if (errs.length) { console.log('ERRORS', errs); process.exit(1); }
