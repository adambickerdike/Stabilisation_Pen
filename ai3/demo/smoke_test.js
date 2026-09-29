#!/usr/bin/env node
/* Smoke test for the spelling-pen prototype (ai3/demo/index.html).

     python3 -m ai3.demo.build                      (writes index.html and fixtures.json)
     NODE_PATH=$(npm root -g) node ai3/demo/smoke_test.js [--shots DIR] [--page ai3/demo/index.html]

   The page is served by this script from a temporary folder, wrapped in the same document skeleton the artifact
   host adds at publish time.  Checks, at 1280 x 900 and 390 x 844, in light and dark:
     no page or console errors; no request to any other host (the page must make no network calls);
     no horizontal page scroll;
     the example page loads: five words read, the misspelling flagged with the right suggestion;
     the in-page recogniser gives the Python model's answer on 26 real test letters (fixtures.json);
     a word written through the page's own pipeline gets completions at a pause; accepting one records a
     transcript change and makes a writing plan; the pen writes it; the ink record then holds pen-written strokes
     and its hash chain verifies;
     accepting a spelling suggestion changes the transcript only (the ink record and the plans are unchanged);
     mouse strokes on the pad are read as letters;
     the 'lift the pen' cue withholds ink on a misspelled word.
   Screenshots go to --shots.  Exit code 1 when a check fails. */
"use strict";
const fs = require("fs"), path = require("path"), http = require("http"), os = require("os");
const args = process.argv.slice(2);
const arg = (n, d) => { const i = args.indexOf(n); return i >= 0 && i + 1 < args.length ? args[i + 1] : d };
const HERE = __dirname;
const PAGE = path.resolve(arg("--page", path.join(HERE, "index.html")));
const FIX = JSON.parse(fs.readFileSync(path.join(path.dirname(PAGE), PAGE.endsWith("_quick.html") ? "fixtures_quick.json" : "fixtures.json"), "utf8"));
const SHOTS = path.resolve(arg("--shots", path.join(os.tmpdir(), "spellpen_shots")));
fs.mkdirSync(SHOTS, { recursive: true });
const { chromium } = require("playwright");

const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui;background:#fafaf7}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>${fs.readFileSync(PAGE, "utf8")}</body></html>`;
const server = http.createServer((req, res) => { if (req.url === "/" || req.url.startsWith("/index.html")) { res.writeHead(200, { "content-type": "text/html; charset=utf-8" }); res.end(html) } else { res.writeHead(404); res.end() } });

const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`) }

async function run(browser, url, label, viewport, scheme) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1, colorScheme: scheme });
  const errors = [], foreign = [];
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("console", m => { if (m.type() === "error") errors.push("console: " + m.text()) });
  page.on("request", r => { const u = new URL(r.url()); if (!["127.0.0.1", "localhost"].includes(u.hostname) && !u.protocol.startsWith("data") && !u.protocol.startsWith("blob")) foreign.push(r.url()) });
  await page.goto(url, { waitUntil: "load" });
  await page.waitForFunction(() => window.__demo && window.__demo.ready, null, { timeout: 120000 });
  const st0 = await page.evaluate(() => ({ s: window.__demo.state(), errs: window.__demo.errors }));
  check(`${label}: page ready without script errors`, !st0.errs.length && !errors.length, [...st0.errs, ...errors].join(" | ").slice(0, 300));
  const ov = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  check(`${label}: no horizontal page scroll`, ov[0] <= ov[1], `scrollWidth ${ov[0]} / viewport ${ov[1]}`);
  const ex = st0.s.words;
  const flagged = ex.find(w => w.flags.some(f => f.kind === "spelling"));
  check(`${label}: example page: five words read, the misspelling flagged`, ex.length === 5 && !!flagged,
    ex.map(w => w.literal + (w.flags.some(f => f.kind === "spelling") ? "*" : "")).join(" "));
  const sugg = flagged ? (flagged.flags.find(f => f.kind === "spelling").sugg || []).map(s => s.w) : [];
  check(`${label}: the flagged word's suggestions include "library"`, sugg.includes("library"), sugg.join(", "));
  await page.screenshot({ path: path.join(SHOTS, `${label}_example.png`), fullPage: true });
  if (label.startsWith("desktop-light")) {
    /* 1. the recogniser gives Python's answers */
    const cmp = await page.evaluate(fx => fx.map(f => { const p = window.__demo.recognise(f.strokes); let k = 0; for (let i = 1; i < 26; i++) if (p[i] > p[k]) k = i;
      let d = 0; for (let i = 0; i < 26; i++) d = Math.max(d, Math.abs(p[i] - f.p[i])); return { char: f.char, py: f.top1, js: "abcdefghijklmnopqrstuvwxyz"[k], d } }), FIX.letters);
    const same = cmp.filter(c => c.py === c.js).length, dmax = Math.max(...cmp.map(c => c.d));
    check(`${label}: in-page recogniser matches the Python model on 26 real test letters`, same >= 25 && dmax < 0.05,
      `${same}/26 same top letter; largest posterior difference ${dmax.toFixed(4)}; Python read ${cmp.filter(c => c.py === c.char).length}/26 right`);
    /* 2. completions at a pause, acceptance, plan, the pen writes */
    await page.evaluate(() => window.__demo.newPage());
    await page.evaluate(w => window.__demo.writeWordXh(w, true), FIX.words.becau);
    await page.waitForTimeout(300);
    let s = await page.evaluate(() => window.__demo.state());
    check(`${label}: a pause after "becau" offers completions including "because"`, s.tray && s.trayWords.includes("because"), `tray ${s.tray}: ${s.trayWords.join(", ")}`);
    const rec0 = s.record;
    if (s.trayWords.includes("because")) await page.click('#trayopts button[data-w="because"]');
    s = await page.evaluate(() => window.__demo.state());
    check(`${label}: accepting it logs a transcript change and makes a writing plan (planned, not yet ink)`, s.revs >= 1 && s.plans.length === 1 && s.plans[0].state === "planned" && s.record === rec0,
      `revisions ${s.revs}, plans ${JSON.stringify(s.plans)}, record ${rec0} -> ${s.record}`);
    await page.screenshot({ path: path.join(SHOTS, `${label}_plan.png`), fullPage: true });
    await page.evaluate(() => window.__demo.runPlan());
    s = await page.evaluate(() => window.__demo.state());
    const ok = await page.evaluate(() => window.__demo.verifyRecord());
    check(`${label}: the pen writes the accepted letters; the record holds them and its hash chain verifies`, s.plans[0].state === "written" && s.record > rec0 && ok,
      `plan ${s.plans[0].state}; record ${rec0} -> ${s.record}; chain ${ok}`);
    /* 3. a spelling suggestion changes the transcript only */
    await page.evaluate(w => window.__demo.writeWordXh(w, false), FIX.words.libary);
    await page.evaluate(() => window.__demo.endWord());
    s = await page.evaluate(() => window.__demo.state());
    const last = s.words[s.words.length - 1], sp = last.flags.find(f => f.kind === "spelling");
    check(`${label}: "libary" written on the pad is flagged with "library"`, !!sp && sp.sugg.some(x => x.w === "library"), `${last.literal}: ${JSON.stringify(last.flags).slice(0, 160)}`);
    const before = { rec: s.record, plans: s.plans.length };
    const btn = await page.$('#detail button:has-text("library")');
    if (btn) await btn.click();
    s = await page.evaluate(() => window.__demo.state());
    check(`${label}: accepting "library" changes the transcript only (ink record and plans unchanged)`, s.words[s.words.length - 1].text === "library" && s.record === before.rec && s.plans.length === before.plans,
      `text ${s.words[s.words.length - 1].text}; record ${before.rec} -> ${s.record}; plans ${before.plans} -> ${s.plans.length}`);
    await page.screenshot({ path: path.join(SHOTS, `${label}_after.png`), fullPage: true });
    /* 4. mouse strokes on the pad */
    const box = await page.$eval("#pad", el => { const r = el.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height } });
    const o = FIX.letters.find(f => f.char === "o"), XH = box.w < 520 ? 34 : 44, base = Math.round(XH * 2.55);
    const pts = o.strokes[0], xs = pts.map(p => p[0]), ys = pts.map(p => p[1]), x0 = Math.min(...xs), y0 = Math.min(...ys);
    await page.mouse.move(box.x + 40 + (pts[0][0] - x0) * XH, box.y + base - (pts[0][1] - y0) * XH);
    await page.mouse.down();
    for (const p of pts.slice(1)) await page.mouse.move(box.x + 40 + (p[0] - x0) * XH, box.y + base - (p[1] - y0) * XH, { steps: 2 });
    await page.mouse.up();
    await page.waitForTimeout(200);
    const live = await page.$$eval("#live .lchip", els => els.map(e => e.textContent));
    check(`${label}: a letter drawn with the mouse is read ("o" from a real test letter)`, live.length === 1 && live[0] === "o", `live letters: ${live.join("")}`);
    await page.evaluate(() => window.__demo.endWord());
    /* 5. the pen-lift cue */
    await page.evaluate(() => window.__demo.setCue("withhold"));
    await page.evaluate(w => window.__demo.writeWordXh(w, false), FIX.words.libary);
    s = await page.evaluate(() => window.__demo.state());
    const withheld = await page.evaluate(() => document.getElementById("inkmeta").textContent);
    check(`${label}: with "lift the pen" chosen, the pen cue fires on "libary" mid-word`, ["withhold", "tick"].includes(s.cue), `pen state ${s.cue}; ${withheld}`);
    await page.screenshot({ path: path.join(SHOTS, `${label}_cue.png`), fullPage: true });
    await page.evaluate(() => window.__demo.endWord());
  }
  check(`${label}: no requests to other hosts`, !foreign.length, foreign.slice(0, 3).join(", "));
  await page.close();
}

(async () => {
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  const url = `http://127.0.0.1:${server.address().port}/index.html`;
  const browser = await chromium.launch();
  try {
    await run(browser, url, "desktop-light", { width: 1280, height: 900 }, "light");
    await run(browser, url, "desktop-dark", { width: 1280, height: 900 }, "dark");
    await run(browser, url, "phone-light", { width: 390, height: 844 }, "light");
    await run(browser, url, "phone-dark", { width: 390, height: 844 }, "dark");
  } catch (e) { check("test run", false, String(e && e.stack || e).slice(0, 400)) }
  await browser.close(); server.close();
  const failed = results.filter(r => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} checks passed; screenshots in ${SHOTS}`);
  process.exit(failed ? 1 : 0);
})();
