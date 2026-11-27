// node scripts/pack_shots.mjs <extracted pack folder> -> start-here.png and review.png, as a reader's browser shows them offline.
import fs from 'fs'; import path from 'path'; import { pathToFileURL } from 'url'; import { chromium } from 'playwright';
const dir = process.argv[2];
const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1600, height: 1100 }, offline: true });
const failed = []; const p = await ctx.newPage();
p.on('requestfailed', r => failed.push(r.url())); p.on('pageerror', e => failed.push('pageerror ' + e.message));
await p.goto(pathToFileURL(path.join(dir, 'Start here.html')).href); await p.waitForLoadState('load');
await p.screenshot({ path: path.join(dir, 'start-here.png') });
const links = await p.$$eval('a', as => as.map(a => a.getAttribute('href')));
const review = links.find(h => h && h.endsWith('review.html'));
await p.goto(pathToFileURL(path.join(dir, decodeURIComponent(review))).href); await p.waitForLoadState('load');
await p.screenshot({ path: path.join(dir, 'review.png') });
const text = await p.evaluate(() => document.body.innerText);
const missing = links.filter(h => h && !h.startsWith('#') && !h.startsWith('http') && !fs.existsSync(path.join(dir, decodeURIComponent(h))));
console.log(JSON.stringify({ links, missing, failed, review_chars: text.length, review_start: text.slice(0, 400) }, null, 1));
await b.close();
