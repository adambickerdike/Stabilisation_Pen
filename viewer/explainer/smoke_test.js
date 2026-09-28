#!/usr/bin/env node
/* Smoke test for the Rev H explainer page (viewer/explainer/index.html).

   The page loads three.js from two CDNs.  For an offline test, serve a TEST COPY in which those two URLs point to
   local copies of the same files:

     1. python3 viewer/explainer/build.py
     2. node viewer/explainer/smoke_test.js --prepare DIR --three PATH/three.min.js --orbit PATH/OrbitControls.js
        (writes DIR/index.html with local script URLs, DIR/data/*.json and the two three.js files)
     3. in another terminal:  cd DIR && python3 -m http.server 8791 --bind 127.0.0.1
     4. NODE_PATH=$(npm root -g) node viewer/explainer/smoke_test.js --url http://127.0.0.1:8791/index.html --shots DIR/shots

   Checks, at 1360 x 900 and at 390 x 844: no page errors and no console errors (Google Fonts TLS errors in a
   sandbox are ignored); no horizontal page scroll; the 3-D pen draws, the legend and the part selection work
   (legend click, and a click on the canvas over a part); "Take apart" moves the parts; the tip pad moves the nose;
   each of the five scenes plays and draws ink; in the board scene the magnet rides on the handle, the board's head
   sits under it, the pull stays within the limit and the ink ends closer to the letter than the sleeve; the toggles
   work; the handwriting panels render and magnify.
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
const SECTIONS = [["top", "header.top"], ["pen", "#pen"], ["scenes", "#scenes"], ["grip", "#grip"], ["results", "#results"],
                  ["inside", "#inside"], ["who", "#who"], ["limits", "#limits"]];
const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail: detail || "" }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`); }

async function run(browser, label, viewport) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("console", m => { if (m.type() === "error" && !IGNORE.test(m.text())) errors.push("console: " + m.text()); });
  page.on("requestfailed", r => { if (!IGNORE.test(r.url() + " " + (r.failure() && r.failure().errorText))) errors.push("request failed: " + r.url()); });
  await page.goto(URL, { waitUntil: "load" });
  await page.waitForFunction(() => window.__explainer && window.__explainer.ready, null, { timeout: 45000 });
  await page.waitForTimeout(1200);
  const T = () => page.evaluate(() => { const E = window.__explainer; return { errors: E.errors, data: E.data && { layout: E.data.layout, board: E.data.board, samples: E.data.samples },
    hero: !!E.hero, scenes: !!E.scenes, parts: E.hero ? E.hero.pen.parts.length : 0, panels: E.results ? E.results.panels : 0 }; });
  const t0 = await T();
  check(`${label}: page ready, data loaded`, t0.data && t0.data.layout && t0.data.samples, JSON.stringify(t0.data));
  check(`${label}: 3-D pen and scenes built`, t0.hero && t0.scenes && t0.parts > 10, `${t0.parts} parts`);
  const ov = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  check(`${label}: no horizontal page scroll`, ov[0] <= ov[1], `scrollWidth ${ov[0]} / viewport ${ov[1]}`);

  /* sections */
  for (const [name, sel] of SECTIONS) {
    const el = await page.$(sel);
    if (!el) { check(`${label}: section ${name} present`, false); continue; }
    await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(name === "scenes" ? 1500 : 500);
    await el.screenshot({ path: path.join(SHOTS, `${label}_${name}.png`) });
  }

  /* hero: legend, picking, explode, pad */
  await (await page.$("#pen")).scrollIntoViewIfNeeded();
  const nLegend = await page.$$eval("#legend li", l => l.length);
  check(`${label}: legend lists the part groups`, nLegend >= 6, `${nLegend} groups`);
  await page.click("#legend li[data-group='power'] button.pick").catch(() => {});
  await page.waitForTimeout(300);
  const sel1 = await page.textContent("#info-name");
  check(`${label}: legend click selects a group`, /Battery|cell/i.test(sel1), sel1);
  const target = await page.evaluate(() => { const H = window.__explainer.hero; const id = (H.pen.parts.find(m => m.userData.group === "actuator") || H.pen.parts[5]).userData.id; return { id, xy: H.screenOf(id) }; });
  if (target.xy) { await page.mouse.click(target.xy[0], target.xy[1]); await page.waitForTimeout(400); }
  const sel2 = await page.evaluate(() => { const H = window.__explainer.hero; return H.sel ? (H.sel.part || H.sel.group) : null; });
  check(`${label}: click on the 3-D pen selects a part`, !!sel2 && sel2 !== "power", `clicked ${target.id}, selected ${sel2}`);
  const labels = await page.$$eval("#hero-labels .lab", l => l.filter(x => !x.hidden).length);
  check(`${label}: labels shown`, labels > 0, `${labels} labels`);
  await page.$eval("#explode", el => { el.value = "100"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.waitForTimeout(1800);
  const ex = await page.evaluate(() => window.__explainer.hero.explode);
  check(`${label}: "Take apart" separates the parts`, ex > 0.9, `explode ${ex.toFixed(2)}`);
  await (await page.$("#hero-vp")).screenshot({ path: path.join(SHOTS, `${label}_pen_exploded.png`) });
  await page.$eval("#explode", el => { el.value = "0"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.click("#xray"); await page.waitForTimeout(300);
  const xr = await page.evaluate(() => window.__explainer.hero.xray);
  check(`${label}: X-ray toggles`, xr === false);
  await page.click("#xray");
  await page.evaluate(() => window.__explainer.hero.padSet(45, 0));
  await page.waitForTimeout(600);
  const tip = await page.evaluate(() => window.__explainer.hero.tip[0]);
  check(`${label}: tip pad tilts the nose`, tip > 1.5, `tip offset ${tip.toFixed(2)} mm`);
  await page.waitForTimeout(1500);

  /* scenes */
  await (await page.$(".scene-grid")).scrollIntoViewIfNeeded();
  for (const k of ["a", "b", "c", "d", "e"]) {
    await page.click(`.scene-btn[data-scene='${k}']`);
    await page.waitForTimeout(250);
    await page.evaluate(() => { const S = window.__explainer.scenes; S.seek(S.S.T * 0.8); });
    await page.waitForTimeout(350);
    const st = await page.evaluate(() => window.__explainer.scenes.stats());
    const pressed = await page.getAttribute(`.scene-btn[data-scene='${k}']`, "aria-pressed");
    check(`${label}: scene ${k} plays and draws ink`, st.key === k && pressed === "true" && st.inkTriangles > 10 && (k !== "e" || st.board > 3),
      `${st.samples} samples, ${Math.round(st.inkTriangles)} ink triangles${st.fromData ? ", simulation data" : ""}${k === "e" ? `, ${st.board} board parts` : ""}`);
    if (k === "e") {
      const bc = st.boardCheck || {};
      const r = bc.rms || [];
      check(`${label}: board pulls the sleeve magnet, the nose fixes the rest`,
        bc.onHandle === true && bc.headToMagnetMm != null && bc.headToMagnetMm < 5 && r.length === 3 && r[0] > r[1] && r[1] > r[2] && bc.maxPullN <= bc.capN + 1e-9,
        `magnet on the handle: ${bc.onHandle}; head ${bc.headToMagnetMm != null ? bc.headToMagnetMm.toFixed(1) : "?"} mm from it; ` +
        `off the letter ${r.map(x => x.toFixed(2)).join(" > ")} mm (hand alone, sleeve, ink); pull max ${bc.maxPullN != null ? bc.maxPullN.toFixed(2) : "?"} N <= ${bc.capN} N`);
    }
    await (await page.$(".scene-grid")).screenshot({ path: path.join(SHOTS, `${label}_scene_${k}.png`) });
  }
  await page.click(".scene-btn[data-scene='b']");
  await page.click("[data-trk='today']"); await page.waitForTimeout(200);
  const trk = await page.evaluate(() => window.__explainer.scenes.trk);
  check(`${label}: stabiliser quality toggle`, trk === "today");
  await page.click("[data-view='hand']"); await page.waitForTimeout(300);
  const vw = await page.evaluate(() => window.__explainer.scenes.stats().view);
  check(`${label}: whole-hand view toggle`, vw === "hand");
  await page.click("[data-mag='3']"); await page.waitForTimeout(200);
  const mg = await page.evaluate(() => window.__explainer.scenes.stats().mag);
  check(`${label}: motion magnify toggle`, mg === 3);
  await page.click("[data-mag='1']"); await page.click("[data-view='tip']");

  /* results */
  const panels = await page.$$eval("#results-body .rpanel", l => l.length);
  check(`${label}: handwriting panels render`, panels > 0, `${panels} panels`);
  const w1 = await page.$eval(".strip svg", s => s.getBoundingClientRect().width);
  await page.click("[data-zoom='3']"); await page.waitForTimeout(200);
  const w3 = await page.$eval(".strip svg", s => s.getBoundingClientRect().width);
  check(`${label}: "Magnified x3" enlarges the strips`, w3 > 2.5 * w1, `${w1.toFixed(0)} -> ${w3.toFixed(0)} px`);
  await page.click("[data-zoom='1']");
  const ov2 = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
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
    /* dark theme: one look at the page top and the 3-D pen */
    const ctx = await browser.newContext({ viewport: { width: 1360, height: 900 }, colorScheme: "dark" });
    const p = await ctx.newPage();
    await p.goto(URL, { waitUntil: "load" });
    await p.waitForFunction(() => window.__explainer && window.__explainer.ready, null, { timeout: 45000 });
    await p.waitForTimeout(1200);
    for (const [name, sel] of [["pen", "#pen"], ["results", "#results"]]) { const el = await p.$(sel); await el.scrollIntoViewIfNeeded(); await p.waitForTimeout(400); await el.screenshot({ path: path.join(SHOTS, `dark_${name}.png`) }); }
    await ctx.close();
  } catch (e) { check("test run", false, e.message); }
  await browser.close();
  const failed = results.filter(r => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed; screenshots in ${SHOTS}`);
  process.exit(failed.length ? 1 : 0);
})();
