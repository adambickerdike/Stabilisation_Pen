#!/usr/bin/env node
/* Smoke test for the Rev J explainer page (viewer/explainer/index.html).

   The page loads three.js from two CDNs.  For an offline test, serve a TEST COPY in which those two URLs point to
   local copies of the same files:

     1. python3 viewer/explainer/build.py
     2. node viewer/explainer/smoke_test.js --prepare DIR --three PATH/three.min.js --orbit PATH/OrbitControls.js
        (writes DIR/index.html with local script URLs, DIR/data/*.json and the two three.js files)
     3. in another terminal:  cd DIR && python3 -m http.server 8791 --bind 127.0.0.1
     4. NODE_PATH=$(npm root -g) node viewer/explainer/smoke_test.js --url http://127.0.0.1:8791/index.html --shots DIR/shots

   Checks, at 1360 x 900 and at 390 x 844: no page errors and no console errors (Google Fonts TLS errors in a sandbox
   are ignored); no horizontal page scroll; the 3-D pen draws with the Rev J groups (heel drive, end-cap); the legend
   and part selection work (legend click, and a click on the canvas over a part); the three numbered pins (tip, heel,
   tail) show and select their group; "Take apart" moves the parts; the end-cap toggle takes the end-cap off and puts
   the rear cap on; the tip pad tilts the nose, slides the refill and steers the heel wheel; the camera buttons; each
   of the six scenes plays and draws ink (a, b and f from simulation data; the wheel steers through the loops of c; the
   nose writes in f; the push arrow and the "set on a b" writer in e); the stabiliser choice in b; the physics chart and
   the mode pictures draw; the results table and the handwriting strips render and magnify.
   Screenshots of every section (and of every scene) go to --shots.  Exit code 1 when a check fails. */
"use strict";
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const arg = (name, dflt) => { const i = args.indexOf(name); return i >= 0 && i + 1 < args.length ? args[i + 1] : dflt; };
const HERE = __dirname;

/* ------------------------------------------------------------------------------------------ --prepare DIR */
if (args.includes("--prepare")) {
  const dir = path.resolve(arg("--prepare"));
  const three = arg("--three"), orbit = arg("--orbit");
  fs.mkdirSync(path.join(dir, "data"), { recursive: true });
  let html = fs.readFileSync(path.join(HERE, "index.html"), "utf8");
  const n0 = html.length;
  html = html.replace("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js", "three.min.js")
             .replace("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js", "OrbitControls.js");
  if (html.length === n0) { console.error("prepare: the CDN script URLs were not found in index.html"); process.exit(1); }
  fs.writeFileSync(path.join(dir, "index.html"), html);
  for (const f of fs.readdirSync(path.join(dir, "data"))) fs.unlinkSync(path.join(dir, "data", f));     /* no stale data files */
  for (const f of fs.readdirSync(path.join(HERE, "data"))) fs.copyFileSync(path.join(HERE, "data", f), path.join(dir, "data", f));
  if (three) fs.copyFileSync(three, path.join(dir, "three.min.js"));
  if (orbit) fs.copyFileSync(orbit, path.join(dir, "OrbitControls.js"));
  for (const f of ["three.min.js", "OrbitControls.js"]) if (!fs.existsSync(path.join(dir, f))) console.warn(`prepare: ${f} missing in ${dir} (pass --three / --orbit)`);
  console.log(`prepared ${dir}`);
  process.exit(0);
}

/* ------------------------------------------------------------------------------------------------- test */
const { chromium } = require("playwright");
const URL = arg("--url", process.env.EXPLAINER_URL || "http://127.0.0.1:8791/index.html");
const SHOTS = path.resolve(arg("--shots", process.env.EXPLAINER_SHOTS || path.join(require("os").tmpdir(), "explainer_shots")));
fs.mkdirSync(SHOTS, { recursive: true });
const IGNORE = /fonts\.(googleapis|gstatic)\.com|ERR_CERT_AUTHORITY_INVALID|net::ERR_CERT/;
const SECTIONS = [["top", "header.top"], ["pen", "#pen"], ["how", "#how"], ["modes", "#modes"], ["results", "#results"],
                  ["grip", "#grip"], ["inside", "#inside"], ["who", "#who"], ["limits", "#limits"], ["changes", "#changes"]];
const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail: detail || "" }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`); }
const noScroll = page => page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);

async function run(browser, label, viewport) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("console", m => { if (m.type() === "error" && !IGNORE.test(m.text())) errors.push("console: " + m.text()); });
  page.on("requestfailed", r => { if (!IGNORE.test(r.url() + " " + (r.failure() && r.failure().errorText))) errors.push("request failed: " + r.url()); });
  await page.goto(URL, { waitUntil: "load" });
  await page.waitForFunction(() => window.__explainer && window.__explainer.ready, null, { timeout: 60000 });
  await page.waitForTimeout(1500);
  const T = () => page.evaluate(() => { const E = window.__explainer; return { errors: E.errors, data: E.data && { layout: E.data.layout, facts: E.data.facts, samples: E.data.samples, replay: E.data.replay },
    hero: !!E.hero, scenes: !!E.scenes, parts: E.hero ? E.hero.pen.parts.length : 0, panels: E.results ? E.results.panels : 0,
    groups: E.hero ? [...new Set(E.hero.pen.parts.map(m => m.userData.group))] : [] }; });
  const t0 = await T();
  check(`${label}: page ready, data loaded`, t0.data && t0.data.layout && t0.data.facts && t0.data.samples, JSON.stringify(t0.data));
  check(`${label}: 3-D pen and scenes built, with the heel drive and the end-cap`, t0.hero && t0.scenes && t0.parts > 30 && t0.groups.includes("drive") && t0.groups.includes("inertial"),
    `${t0.parts} parts; groups ${t0.groups.join(", ")}`);
  const ov = await noScroll(page);
  check(`${label}: no horizontal page scroll`, ov[0] <= ov[1], `scrollWidth ${ov[0]} / viewport ${ov[1]}`);

  /* sections */
  for (const [name, sel] of SECTIONS) {
    const el = await page.$(sel);
    if (!el) { check(`${label}: section ${name} present`, false); continue; }
    await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(name === "how" ? 1500 : 500);
    await el.screenshot({ path: path.join(SHOTS, `${label}_${name}.png`) });
  }

  /* hero: legend, picking, pins, explode, end-cap, pad */
  await (await page.$("#pen")).scrollIntoViewIfNeeded(); await page.waitForTimeout(400);
  const nLegend = await page.$$eval("#legend li", l => l.length);
  check(`${label}: legend lists the part groups`, nLegend >= 10, `${nLegend} groups`);
  await page.click("#legend li[data-group='power'] button.pick").catch(() => {});
  await page.waitForTimeout(300);
  const sel1 = await page.textContent("#info-name");
  check(`${label}: legend click selects a group`, /Battery|cell/i.test(sel1), sel1);
  const target = await page.evaluate(() => { const H = window.__explainer.hero; const id = (H.pen.parts.find(m => m.userData.id === "coil_plate") || H.pen.parts.find(m => m.userData.group === "actuator")).userData.id; return { id, xy: H.screenOf(id) }; });
  if (target.xy) { await page.mouse.click(target.xy[0], target.xy[1]); await page.waitForTimeout(400); }
  const sel2 = await page.evaluate(() => { const H = window.__explainer.hero; return H.sel ? (H.sel.part || H.sel.group) : null; });
  check(`${label}: click on the 3-D pen selects a part`, !!sel2 && sel2 !== "power", `clicked ${target.id}, selected ${sel2}`);
  const labels = await page.$$eval("#hero-labels .lab", l => l.filter(x => !x.hidden).length);
  check(`${label}: labels shown`, labels > 0, `${labels} labels`);
  const pins = await page.evaluate(() => window.__explainer.hero.pinsShown());
  check(`${label}: the three action points are marked (tip, heel, tail)`, ["tip", "heel", "tail"].every(k => pins.includes(k)), pins.join(", "));
  await page.click(".pin[data-act='heel']").catch(() => {}); await page.waitForTimeout(300);
  const selHeel = await page.evaluate(() => { const H = window.__explainer.hero; return { g: H.sel && H.sel.group, name: document.getElementById("info-name").textContent }; });
  check(`${label}: the heel pin selects the heel drive`, selHeel.g === "drive" && /Heel/.test(selHeel.name), `${selHeel.g}: ${selHeel.name}`);
  await page.$eval("#explode", el => { el.value = "100"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.waitForFunction(() => window.__explainer.hero.explode > 0.9, null, { timeout: 8000 }).catch(() => {});
  const ex = await page.evaluate(() => window.__explainer.hero.explode);
  check(`${label}: "Take apart" separates the parts`, ex > 0.9, `explode ${ex.toFixed(2)}`);
  await (await page.$("#hero-vp")).screenshot({ path: path.join(SHOTS, `${label}_pen_exploded.png`) });
  await page.$eval("#explode", el => { el.value = "0"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.waitForFunction(() => window.__explainer.hero.explode < 0.02, null, { timeout: 8000 }).catch(() => {});
  await page.click("#xray"); await page.waitForTimeout(300);
  const xr = await page.evaluate(() => window.__explainer.hero.xray);
  check(`${label}: X-ray toggles`, xr === false);
  await page.click("#xray");
  /* end-cap off: its parts hide, the rear cap shows; then back on */
  await page.click("#endcap"); await page.waitForTimeout(300);
  const ec0 = await page.evaluate(() => { const P = window.__explainer.hero.pen; return { on: P.endcap, ec: P.parts.filter(m => m.userData.group === "inertial").some(m => m.visible),
    cap: P.parts.filter(m => m.userData.comp.replaced_by_endcap).every(m => m.visible), len: P.length(), pressed: document.getElementById("endcap").getAttribute("aria-pressed") }; });
  await (await page.$("#hero-vp")).screenshot({ path: path.join(SHOTS, `${label}_pen_no_endcap.png`) });
  await page.click("#endcap"); await page.waitForTimeout(300);
  const ec1 = await page.evaluate(() => { const P = window.__explainer.hero.pen; return { on: P.endcap, ec: P.parts.filter(m => m.userData.group === "inertial").every(m => m.visible), len: P.length() }; });
  check(`${label}: end-cap toggle (off: rear cap on; on: end-cap back)`, ec0.on === false && !ec0.ec && ec0.cap && ec0.pressed === "false" && ec1.on === true && ec1.ec && ec1.len > ec0.len,
    `off ${ec0.len.toFixed(1)} mm, on ${ec1.len.toFixed(1)} mm`);
  /* the tip pad: the nose tilts, the refill slides, the heel wheel steers */
  const rest = await page.evaluate(() => { const P = window.__explainer.hero.pen; return { z: P.refillG.position.z, psi: P.psi }; });
  await page.evaluate(() => window.__explainer.hero.padSet(45, 0));
  await page.waitForTimeout(900);
  const moved = await page.evaluate(() => { const H = window.__explainer.hero, P = H.pen; return { tip: Math.hypot(H.tip[0], H.tip[1]), psi: P.psi, z: P.refillG.position.z, read: document.getElementById("pad-read").textContent }; });
  check(`${label}: tip pad tilts the nose, slides the refill and steers the heel wheel`,
    moved.tip > 3 && Math.abs(moved.z - rest.z) > 0.05 && Math.abs(moved.psi - rest.psi) > 0.3,
    `tip ${moved.tip.toFixed(2)} mm; refill slid ${(moved.z - rest.z).toFixed(2)} mm; wheel turned ${(Math.abs(moved.psi - rest.psi) * 180 / Math.PI).toFixed(0)}°; "${moved.read}"`);
  await page.click("#cam-tip"); await page.waitForTimeout(700);
  await (await page.$("#hero-vp")).screenshot({ path: path.join(SHOTS, `${label}_pen_tip_heel.png`) });
  const pinsTip = await page.evaluate(() => window.__explainer.hero.pinsShown());
  await page.click("#cam-tail"); await page.waitForTimeout(700);
  await (await page.$("#hero-vp")).screenshot({ path: path.join(SHOTS, `${label}_pen_tail.png`) });
  const pinsTail = await page.evaluate(() => window.__explainer.hero.pinsShown());
  check(`${label}: camera views (tip and heel; tail)`, pinsTip.includes("heel") && pinsTip.includes("tip") && pinsTail.join() === "tail", `tip view pins ${pinsTip.join("+")}; tail view pins ${pinsTail.join("+")}`);
  await page.click("#cam-side"); await page.evaluate(() => window.__explainer.hero.padSet(0, 0));
  await page.waitForTimeout(600);

  /* the physics chart and the mode pictures */
  const ph = await page.evaluate(() => ({ p: window.__explainer.physics, minis: window.__explainer.minis }));
  check(`${label}: physics chart (tail weight, heel wheel) and mode pictures drawn`, ph.p && ph.p.points >= 5 && ph.p.traction >= 2 && ph.minis >= 15,
    `${ph.p ? ph.p.points : 0} points, ${ph.p ? ph.p.traction : 0} friction values, ${ph.minis} mode marks`);

  /* scenes */
  await (await page.$(".scene-grid")).scrollIntoViewIfNeeded();
  for (const k of ["a", "b", "c", "d", "e", "f"]) {
    await page.click(`.scene-btn[data-scene='${k}']`);
    await page.waitForTimeout(250);
    await page.evaluate(() => { const S = window.__explainer.scenes; S.seek(S.S.T * 0.8); });
    await page.waitForTimeout(350);
    const st = await page.evaluate(() => window.__explainer.scenes.stats());
    const pressed = await page.getAttribute(`.scene-btn[data-scene='${k}']`, "aria-pressed");
    const needData = k === "a" || k === "b" || k === "f";
    check(`${label}: scene ${k} plays and draws ink`, st.key === k && pressed === "true" && st.inkTriangles > 10 && (!needData || st.fromData),
      `${st.samples} samples, ${Math.round(st.inkTriangles)} ink triangles${st.fromData ? ", simulation data" : ", illustration"}`);
    if (k === "c") {
      const range = await page.evaluate(() => window.__explainer.scenes.headingSweep());
      check(`${label}: scene c, the heel wheel steers along the loops`, range > 1.5, `heading range ${(range * 180 / Math.PI).toFixed(0)}°`);
    }
    if (k === "f") check(`${label}: scene f, the nose writes the letters (autowrite)`, st.noseMax > 2 && st.noseMax < 7.5, `largest nose offset ${st.noseMax.toFixed(2)} mm`);
    if (k === "e") {
      const ar = await page.evaluate(() => { const S = window.__explainer.scenes, was = S.playing; S.playing = false; S.seek(S.S.T * 0.4); const r = S.stats(); S.playing = was; return r; });
      await page.click("[data-writer='b']"); await page.waitForTimeout(250);
      const bs = await page.evaluate(() => { const S = window.__explainer.scenes, was = S.playing; S.playing = false; S.seek(S.S.T * 0.5); const r = S.stats(); S.playing = was; return r; });
      await (await page.$(".scene-grid")).screenshot({ path: path.join(SHOTS, `${label}_scene_e_setonb.png`) });
      check(`${label}: scene e, the wheel pushes; a writer set on a 'b' keeps it`, ar.arrow && bs.bset && bs.arrow && bs.inkTriangles > 10, `push arrow ${ar.arrow}; 'b' writer ${bs.bset}`);
      await page.click("[data-writer='relaxed']"); await page.waitForTimeout(200);
      await page.evaluate(() => { const S = window.__explainer.scenes; S.seek(S.S.T * 0.8); });
    }
    await (await page.$(".scene-grid")).screenshot({ path: path.join(SHOTS, `${label}_scene_${k}.png`) });
  }
  await page.click(".scene-btn[data-scene='b']"); await page.waitForTimeout(200);
  const trkBtns = await page.$$eval("[data-trk]", l => l.map(b => b.dataset.trk));
  const alt = trkBtns.find(x => x !== "gated" && x !== "today") || trkBtns[0];
  await page.click(`[data-trk='${alt}']`); await page.waitForTimeout(250);
  const trk = await page.evaluate(() => window.__explainer.scenes.stats());
  check(`${label}: stabiliser choice in scene b`, trk.trk === alt && trk.inkTriangles >= 0, `${trkBtns.length} choices; now ${trk.trk}`);
  await page.click(`[data-trk='${trkBtns.includes("gated") ? "gated" : trkBtns[0]}']`);
  await page.click("[data-view='hand']"); await page.waitForTimeout(300);
  const vw = await page.evaluate(() => window.__explainer.scenes.stats().view);
  check(`${label}: whole-hand view toggle`, vw === "hand");
  await page.click("[data-mag='3']"); await page.waitForTimeout(200);
  const mg = await page.evaluate(() => window.__explainer.scenes.stats().mag);
  check(`${label}: motion magnify toggle`, mg === 3);
  await page.click("[data-mag='1']"); await page.click("[data-view='tip']");

  /* results */
  const rows = await page.$$eval("table.res tbody tr", l => l.length);
  check(`${label}: results table`, rows >= 9, `${rows} rows`);
  const panels = await page.$$eval("#results-body .rpanel", l => l.length);
  const conds = await page.$$eval("#results-body .rgroup", l => l.map(g => g.dataset.cond));
  check(`${label}: handwriting strips render (tremor, autowrite, heel)`, panels >= 4 && ["tremor", "autowrite", "heel"].every(c => conds.includes(c)), `${panels} panels; groups ${conds.join(", ")}`);
  await (await page.$("#results-body")).scrollIntoViewIfNeeded(); await page.waitForTimeout(300);
  await (await page.$("#results-body")).screenshot({ path: path.join(SHOTS, `${label}_strips.png`) });
  const w1 = await page.$eval(".strip svg", s => s.getBoundingClientRect().width);
  await page.click("[data-zoom='3']"); await page.waitForTimeout(200);
  const w3 = await page.$eval(".strip svg", s => s.getBoundingClientRect().width);
  check(`${label}: "Magnified x3" enlarges the strips`, w3 > 2.5 * w1, `${w1.toFixed(0)} -> ${w3.toFixed(0)} px`);
  await page.click("[data-zoom='1']");
  const ov2 = await noScroll(page);
  check(`${label}: still no horizontal page scroll after interaction`, ov2[0] <= ov2[1], `scrollWidth ${ov2[0]} / viewport ${ov2[1]}`);

  const t1 = await T();
  const all = errors.concat(t1.errors || []);
  check(`${label}: no page or console errors`, all.length === 0, all.slice(0, 4).join(" | "));
  await page.close();
}

(async () => {
  const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  try {
    await run(browser, "desktop", { width: 1360, height: 900 });
    await run(browser, "phone", { width: 390, height: 844 });
    /* dark theme: one look at the page top, the 3-D pen, the physics and the results */
    const ctx = await browser.newContext({ viewport: { width: 1360, height: 900 }, colorScheme: "dark" });
    const p = await ctx.newPage();
    const derr = [];
    p.on("pageerror", e => derr.push(e.message));
    await p.goto(URL, { waitUntil: "load" });
    await p.waitForFunction(() => window.__explainer && window.__explainer.ready, null, { timeout: 60000 });
    await p.waitForTimeout(1500);
    for (const [name, sel] of [["top", "header.top"], ["pen", "#pen"], ["how", "#how"], ["modes", "#modes"], ["results", "#results"]]) {
      const el = await p.$(sel); await el.scrollIntoViewIfNeeded(); await p.waitForTimeout(500); await el.screenshot({ path: path.join(SHOTS, `dark_${name}.png`) }); }
    check("dark theme: no page errors", derr.length === 0, derr.slice(0, 3).join(" | "));
    await ctx.close();
  } catch (e) { check("test run", false, e.message); }
  await browser.close();
  const failed = results.filter(r => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed; screenshots in ${SHOTS}`);
  process.exit(failed.length ? 1 : 0);
})();
