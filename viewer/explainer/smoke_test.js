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
   are ignored); no horizontal page scroll.
   The simple view: three mechanism sentences with evidence labels; no micrometre numbers above "Details"; the
   to-scale cut-away draws the pen from the layout and its four animations do what the page says (hand shake: the
   handle moves while the ball stays on the line, the inner pen turns, the tail weight moves the other way; writes for
   you: simulation data, ink in the view from above; heel wheel: the wheel steers through the loops; tail weight);
   the labels and arrows are drawn; play, pause and the scrubber work.  The 3-D pen: "what moves" colours by default,
   the part-group legend and part selection, the three numbered pins, the hand shake (the handle moves, the ball stays),
   take apart, see inside, the end-cap toggle, the tip pad, the cameras.  "How much better?": one number per row, an
   evidence label per row, a picture pair where the study saved writing; the honest tracing row (letters read fall).
   "How sure are we?".  "Known problems (being fixed)": right after it, four lines (holding power, heel wheel, page
   sensor, made-up data), each with its evidence label, and the side-load figure (spring, paper, sideways part, magnets'
   force, the two arms, the lever equation; every label inside the drawing).  Every battery-hours and heat figure is
   marked "suspended (see known problems)".  The tail weight is Rev J.1's lighter end-cap in the simple view, the
   first design's 8–20 % only in Details.  "Details": every block is closed at first; opening them draws the physics chart and the mode
   pictures, builds the six scenes (each plays and draws ink), the results table and the strips (which magnify), and
   shows the corrected limits text.
   Screenshots of every section, every cut-away mode, every opened Details block and a dark-theme set go to --shots.
   Exit code 1 when a check fails. */
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
const SECTIONS = [["top", "header.top"], ["moves", "#moves"], ["see", "#see"], ["pen", "#pen"], ["better", "#better"], ["sure", "#sure"], ["known", "#known"], ["details", "#details"]];
const DETAILS = ["d-physics", "d-parts", "d-modes", "d-results", "d-scenes", "d-grip", "d-who", "d-limits", "d-changes", "d-data"];
const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail: detail || "" }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`); }
const noScroll = page => page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
/* scroll without Playwright's frame-stability wait: with software WebGL a frame of a playing scene can take a second */
const show = (page, sel) => page.$eval(sel, el => el.scrollIntoView({ block: "start" }));
const pauseAll = (page, on) => page.evaluate(p => { const E = window.__explainer; if (E.scenes) E.scenes.playing = !p; if (E.cut) E.cut.setPlaying(!p); }, on);
const shot = async (page, sel, file) => { const el = await page.$(sel); if (el) await el.screenshot({ path: path.join(SHOTS, file), timeout: 120000 }); return !!el; };
const openDet = (page, id, open) => page.evaluate(([i, o]) => { const d = document.getElementById(i); if (d) d.open = o; return !!d; }, [id, open]);

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
    hero: !!E.hero, cut: !!E.cut, scenes: !!E.scenes, parts: E.hero ? E.hero.pen.parts.length : 0, panels: E.results ? E.results.panels : 0,
    groups: E.hero ? [...new Set(E.hero.pen.parts.map(m => m.userData.group))] : [] }; });
  const t0 = await T();
  check(`${label}: page ready, data loaded`, t0.data && t0.data.layout && t0.data.facts && t0.data.samples, JSON.stringify(t0.data));
  check(`${label}: 3-D pen built with the heel drive and the end-cap; the cut-away drawn`, t0.hero && t0.cut && t0.parts > 30 && t0.groups.includes("drive") && t0.groups.includes("inertial"),
    `${t0.parts} parts; groups ${t0.groups.join(", ")}`);
  const ov = await noScroll(page);
  check(`${label}: no horizontal page scroll`, ov[0] <= ov[1], `scrollWidth ${ov[0]} / viewport ${ov[1]}`);

  /* ---------------- the simple view ---------------- */
  const simple = await page.evaluate(() => {
    /* micrometres stay out of the simple view, except the page-sensor line of "Known problems" (3 µm against 24–68 µm) */
    const txt = ["#moves", "#see", "#better", "#sure", "header.top"].map(s => (document.querySelector(s) || {}).textContent || "").join(" ");
    const above = ["header.top", "#moves", "#see", "#pen", "#better", "#sure", "#known"].map(s => (document.querySelector(s) || {}).textContent || "").join(" ");
    const mechs = [...document.querySelectorAll("#moves .mech")].map(m => ({ key: m.dataset.mech, bold: m.querySelectorAll(".mech-s b").length, tags: m.querySelectorAll(".tag").length,
      words: (m.querySelector(".mech-s").textContent || "").split(/\s+/).length, sent: (m.querySelector(".mech-s").textContent || "").replace(/\s+/g, " "), note: (m.querySelector(".mech-note") || {}).textContent || "" }));
    const closed = [...document.querySelectorAll("details.det")].map(d => d.open);
    return { um: /µm/.test(txt), mechs, dets: closed.length, anyOpen: closed.some(x => x), first820: /8–20\s*%|8 \/ 18 \/ 20/.test(above) }; });
  check(`${label}: three mechanism sentences (inner pen, heel wheel, tail weight), each with its evidence labels`,
    simple.mechs.length === 3 && ["tip", "heel", "tail"].every(k => simple.mechs.some(m => m.key === k && m.bold >= 2 && m.tags >= 1)),
    simple.mechs.map(m => `${m.key}: ${m.words} words, ${m.tags} labels`).join("; "));
  check(`${label}: no micrometre numbers in the simple view (outside Known problems); ${DETAILS.length} Details blocks, all closed`, !simple.um && simple.dets === DETAILS.length && !simple.anyOpen,
    `µm above Details: ${simple.um}; ${simple.dets} blocks`);
  const mTip = simple.mechs.find(m => m.key === "tip") || {}, mHeel = simple.mechs.find(m => m.key === "heel") || {}, mTail = simple.mechs.find(m => m.key === "tail") || {};
  check(`${label}: mechanisms: the tail is Rev J.1's 17 g weight, not in the product (no gain in the physics simulation; 6–18 % only in the simpler model); the heel wheel is retracted by default; the nib is being redesigned`,
    /\b17\s*g tungsten weight/.test(mTail.sent) && /6–18\s*%/.test(mTail.note) && /no gain/.test(mTail.note) && /Not in the product/.test(mTail.note) && /locked/.test(mTail.note) &&
    /Retracted by default/.test(mHeel.note) && /redesigned/.test(mTip.note) && !simple.first820,
    `tail: "${(mTail.sent || "").slice(0, 60)}…"; heel note: "${(mHeel.note || "").slice(0, 40)}…"; first design's 8–20 % above Details: ${simple.first820}`);
  const rows = await page.evaluate(() => [...document.querySelectorAll("#better .brow")].map(r => ({ id: r.dataset.row, nums: r.querySelectorAll(".bnum .bv").length, thumbs: r.querySelectorAll("svg.thumb").length,
    tags: r.querySelectorAll(".bnum .tag").length, val: (r.querySelector(".bnum .bv") || {}).textContent, verdict: (r.querySelector(".verdict") || {}).textContent || "" })));
  check(`${label}: "How much better?" has one number and an evidence label per row`, rows.length >= 6 && rows.every(r => r.nums === 1 && r.tags >= 1),
    rows.map(r => `${r.id}: ${r.val.replace(/\s+/g, " ").trim()}`).join("; "));
  check(`${label}: picture pairs where the study saved writing (tremor, real tremor, severe tremor with autowrite, loops, clean copy)`,
    ["tremor", "real", "autowrite", "loops", "clean"].every(k => (rows.find(r => r.id === k) || {}).thumbs === 2), rows.map(r => `${r.id} ${r.thumbs}`).join(", "));
  const real = rows.find(r => r.id === "real");
  check(`${label}: the real-tremor row says the pen does not help yet on real tremor`, real && /No help yet on real tremor/.test(real.verdict), real ? `${real.val.replace(/\s+/g, " ").trim()} · ${real.verdict.slice(0, 60)}` : "missing");
  check(`${label}: the rows from the physics simulation: fast shake, slow shake (no help yet), severe shake, loops, tracing, lead-through, tail, clean copy, normal writing`,
    ["tremor", "real", "slow", "autowrite", "loops", "tracing", "spell", "predict", "tail", "collar", "clean", "normal"].every(k => rows.some(r => r.id === k)) &&
    /No help yet/.test((rows.find(r => r.id === "slow") || {}).verdict || ""), rows.map(r => r.id).join(", "));
  const trc = rows.find(r => r.id === "tracing");
  check(`${label}: the tracing row: the half-way nib brings the ink closer (0.83 → 0.64 mm) and stays as readable`, trc && /0\.83\D+0\.64/.test(trc.val) && /readable/.test(trc.verdict), trc ? `${trc.val.trim()} · ${trc.verdict}` : "missing");
  const sure = await page.$eval("#sure", el => el.textContent).catch(() => "");
  check(`${label}: "How sure are we?" says simulation only, not tested on a prototype or people`, /simulation/i.test(sure) && /prototype/.test(sure) && /people/.test(sure), sure.replace(/\s+/g, " ").trim().slice(0, 90));
  const tail = rows.find(r => r.id === "tail");
  check(`${label}: the tail row says no gain in the physics simulation, so it is not in the product; the collar row says no better than locked`,
    tail && /no better/.test(tail.val) && /not in the product/.test(tail.verdict) && /no better/.test((rows.find(r => r.id === "collar") || {}).val || ""), tail ? `${tail.val.replace(/\s+/g, " ").trim()} · ${tail.verdict.slice(0, 80)}` : "missing");

  /* ---------------- known problems (being fixed), with the side-load figure ---------------- */
  const kp = await page.evaluate(() => {
    const k = document.getElementById("known"), sure = document.getElementById("sure");
    let next = sure ? sure.nextElementSibling : null;
    while (next && next.tagName !== "SECTION") next = next.nextElementSibling;
    const items = k ? [...k.querySelectorAll("li[data-kp]")].map(li => ({ key: li.dataset.kp, tags: [...li.querySelectorAll(".tag")].map(t => t.textContent.trim()), text: li.textContent.replace(/\s+/g, " ") })) : [];
    const svg = document.getElementById("sideload"), fig = k && k.querySelector("figure.slfig");
    const texts = svg ? [...svg.querySelectorAll("text")].map(t => t.textContent.replace(/\s+/g, " ")).join(" | ") : "";
    const arrows = svg ? [...svg.querySelectorAll("line.sl-ar")].map(a => [...a.classList].find(c => c !== "sl-ar")) : [];
    let outside = [];
    if (svg) { const vb = svg.viewBox.baseVal;
      for (const t of svg.querySelectorAll("text")) { const b = t.getBBox();
        if (b.x < vb.x - 0.5 || b.y < vb.y - 0.5 || b.x + b.width > vb.x + vb.width + 0.5 || b.y + b.height > vb.y + vb.height + 0.5) outside.push(t.textContent.trim()); } }
    const r = svg ? svg.getBoundingClientRect() : { width: 0, height: 0 };
    return { afterSure: !!next && next.id === "known", inDetails: !!(k && k.closest("details")), heading: ((k && k.querySelector("h2")) || {}).textContent || "",
      items, texts, arrows, outside, w: r.width, h: r.height, eq: ((fig && fig.querySelector(".sl-eq")) || {}).textContent || "",
      cap: ((fig && fig.querySelector("figcaption")) || {}).textContent || "", figTags: fig ? fig.querySelectorAll(".tag").length : 0,
      title: svg ? ((svg.querySelector("title") || {}).textContent || "") : "" }; });
  const it = key => kp.items.find(i => i.key === key) || { text: "", tags: [] };
  check(`${label}: "Known problems (being fixed)" is in the simple view, right after "How sure are we?", four lines each with its evidence label`,
    kp.afterSure && !kp.inDetails && /Known problems \(being fixed\)/.test(kp.heading) && kp.items.length === 4 && kp.items.every(i => i.tags.length >= 1),
    kp.items.map(i => `${i.key}: ${i.tags.join(" + ")}`).join("; "));
  const kS = it("sideload"), kH = it("heel"), kP = it("sensor"), kD = it("data");
  check(`${label}: known problems: holding the ball costs 1.6 W at 50° and 4.7 W at 35°, about 7 times; overheats; battery and heat suspended`,
    /about 7 times harder/.test(kS.text) && /1\.6\s*W at a normal 50°/.test(kS.text) && /4\.7\s*W at 35°/.test(kS.text) && /overheat within about a minute/.test(kS.text) &&
    /balanced nib/.test(kS.text) && /suspended/.test(kS.text) && kS.tags.some(t => /^Calculation/.test(t)) && kS.tags.some(t => /^Simulation/.test(t)), kS.text.slice(0, 110));
  check(`${label}: known problems: heel wheel 0.4 mm, retracted; page sensor 3 µm against DeltaPen's 24–68 µm; made-up writers and shakes`,
    /0\.4\s*mm/.test(kH.text) && /retracted unless the writer turns guidance on/.test(kH.text) && kH.tags.some(t => /^Simulation/.test(t)) &&
    /3\s*µm/.test(kP.text) && /DeltaPen, 2022/.test(kP.text) && /24–68\s*µm/.test(kP.text) && /unproven/.test(kP.text) && kP.tags.some(t => /^Assumption/.test(t)) && kP.tags.some(t => /^Literature/.test(t)) &&
    /made up/.test(kD.text) && /Real recordings/.test(kD.text),
    `${kH.text.slice(0, 50)}… | ${kP.text.slice(0, 60)}… | ${kD.text.slice(0, 40)}…`);
  check(`${label}: side-load figure: spring along the pen, paper's push, its sideways part, the magnets' force, the two arms and the lever equation`,
    ["spring", "paper", "side", "mag"].every(a => kp.arrows.includes(a)) &&
    ["1 · At the ball", "the pen: 0.15 N", "straight up: 0.20 N", "balances the spring", "sideways part:0.126 N", "2 · The inner pen is a lever", "sideways part: 0.126 N",
     "0.84 N: 6.7 times more", "the ball's arm: 76.5 mm", "the magnets' arm:11.5 mm", "pivot"].every(s => kp.texts.includes(s)) &&
    /0\.126\s*N × 76\.5\s*mm = 0\.84\s*N × 11\.5\s*mm/.test(kp.eq) && /6\.7 times harder/.test(kp.cap) && /45\s*s/.test(kp.cap) && kp.figTags >= 2 && kp.title.length > 20,
    `arrows ${kp.arrows.join(", ")}; ${kp.eq.replace(/\s+/g, " ")}`);
  check(`${label}: side-load figure is readable: every label inside the drawing, drawn at least 300 px wide`, kp.outside.length === 0 && kp.w >= 300,
    `${kp.w.toFixed(0)} × ${kp.h.toFixed(0)} px${kp.outside.length ? "; outside: " + kp.outside.join(", ") : ""}`);
  const susp = await page.evaluate(() => {
    const marks = [...document.querySelectorAll("a.susp")];
    const bats = [...document.querySelectorAll(".bat")], batOk = bats.length >= 4 && bats.every(b => b.querySelector("a.susp"));
    const probs = [...document.querySelectorAll(".prob h4")].filter(h => /^(Battery|Warmth)/.test(h.textContent.trim()));
    /* every text with battery hours ("6.1–7.3 h") or a temperature outside the Known problems panel sits in a block that carries the mark */
    const bad = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) { const t = w.currentNode, el = t.parentElement;
      if (!el || el.closest("script, style, svg, #known")) continue;
      if (!/\d(?:\.\d+)?\s*h\b|\bhours?\b|\d\s*°C/.test(t.textContent)) continue;
      const box = el.closest("tr") || el.closest(".prob") || el.closest(".bat") || el.closest(".spec > span") || el.closest("p, li, dd, td, div");
      if (!box || !box.querySelector("a.susp")) bad.push(t.textContent.replace(/\s+/g, " ").trim().slice(0, 70)); }
    return { n: marks.length, linked: marks.every(a => a.getAttribute("href") === "#known"), words: marks.every(a => a.textContent.trim() === "suspended (see known problems)"),
      batOk, bats: bats.length, probOk: probs.length === 2 && probs.every(h => h.querySelector("a.susp")), bad }; });
  check(`${label}: every battery-hours and heat figure is marked "suspended (see known problems)" and links to the panel`,
    susp.n >= 10 && susp.linked && susp.words && susp.batOk && susp.probOk && susp.bad.length === 0,
    `${susp.n} marks; ${susp.bats} mode battery lines; unmarked: ${susp.bad.length ? susp.bad.join(" | ") : "none"}`);

  /* ---------------- the cut-away ---------------- */
  const cut = await page.evaluate(() => { const C = window.__explainer.cut; const probe = m => { const out = []; for (let i = 0; i <= 40; i++) out.push(C.probe(m, i / 40)); return out; };
    const sh = probe("shake"), hl = probe("heel"), tl = probe("tail"), wr = probe("write");
    const maxAbs = (a, f) => Math.max(...a.map(f).map(Math.abs));
    const S = Math.sin(50 * Math.PI / 180);
    return { modes: C.modes, parts: document.querySelectorAll("#cut-body polygon").length, hasData: C.stats().hasData,
      shakeBx: maxAbs(sh, q => q.bx), shakeBall: Math.max(...sh.map(q => Math.hypot(q.ball[0], q.ball[1]))), shakeBeta: maxAbs(sh, q => q.beta), shakeSlug: maxAbs(sh, q => q.slugY),
      slugOpp: tl.filter(q => Math.abs(q.bx) > 0.5).every(q => (q.slugY - q.bx * S) * (-q.bx * S) < 0),
      heelPsi: Math.max(...hl.map(q => q.psi)) - Math.min(...hl.map(q => q.psi)), heelBx: maxAbs(hl, q => q.bx),
      writeRel: maxAbs(wr, q => q.ball[0] - q.bx) }; });
  check(`${label}: cut-away drawn from the layout with four animations`, cut.parts > 30 && ["shake", "write", "heel", "tail"].every(m => cut.modes.includes(m)), `${cut.parts} shapes; modes ${cut.modes.join(", ")}`);
  check(`${label}: hand shake: the handle moves, the inner pen turns, the ball stays on the line`, cut.shakeBx > 3 && cut.shakeBall < 0.05 && cut.shakeBeta > 1,
    `handle ±${cut.shakeBx.toFixed(1)} mm (drawn), ball within ${cut.shakeBall.toFixed(3)} mm, inner pen turns ±${cut.shakeBeta.toFixed(1)}°`);
  check(`${label}: the tail weight moves the other way to the shake`, cut.shakeSlug > 1 && cut.slugOpp, `tail weight ±${cut.shakeSlug.toFixed(1)} mm across the axis`);
  check(`${label}: writes for you: simulation data; the ball moves against the handle`, cut.hasData && cut.writeRel > 2, `ball up to ${cut.writeRel.toFixed(1)} mm from the handle's tip`);
  check(`${label}: heel wheel: the whole pen moves and the wheel steers along the loops`, cut.heelPsi > 2 && cut.heelBx > 2, `heading range ${(cut.heelPsi * 180 / Math.PI).toFixed(0)}°, pen ±${cut.heelBx.toFixed(1)} mm`);
  await pauseAll(page, true);
  for (const m of ["shake", "write", "heel", "tail"]) {
    await page.click(`[data-cut='${m}']`); await page.waitForTimeout(150);
    await page.evaluate(() => { const C = window.__explainer.cut; C.setPlaying(false); C.seek(0.3); });
    const st = await page.evaluate(() => { const C = window.__explainer.cut, s = C.stats(); const vis = [...document.querySelectorAll("#cutsvg .ltxt")].filter(t => t.getComputedTextLength() > 1).length;
      const ink = (document.querySelector("#cutinset .inkp") || { getAttribute: () => "" }).getAttribute("d") || "";
      return { mode: s.mode, labels: s.labels, texts: vis, arrows: document.querySelectorAll("#cut-over .arr").length, key: document.querySelectorAll("#cut-key li").length, inset: s.inset, ink: ink.length,
        pressed: document.querySelector(`[data-cut='${s.mode}']`).getAttribute("aria-pressed") }; });
    const wantText = viewport.width > 700;
    const okInset = m === "write" || m === "heel" ? st.inset && st.ink > 20 : !st.inset;
    check(`${label}: cut-away "${m}": labels, arrows, key${m === "write" || m === "heel" ? " and the view from above" : ""}`,
      st.mode === m && st.pressed === "true" && st.labels >= 3 && st.key === st.labels && (wantText ? st.texts >= st.labels : st.texts === 0) && (m === "write" || st.arrows >= 1) && okInset,
      `${st.labels} labels (${st.texts} texts shown), ${st.arrows} arrows${st.inset ? `, ink path ${st.ink} chars` : ""}`);
    await show(page, "#see"); await page.waitForTimeout(300);
    await shot(page, "#see", `${label}_see_${m}.png`);
  }
  await page.click("[data-cut='shake']");
  const t1c = await page.evaluate(() => window.__explainer.cut.t);
  await page.click("#cut-play"); await page.waitForTimeout(900);
  const t2c = await page.evaluate(() => ({ t: window.__explainer.cut.t, playing: window.__explainer.cut.playing }));
  await page.$eval("#cut-scrub", el => { el.value = "500"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  const t3c = await page.evaluate(() => ({ t: window.__explainer.cut.t, playing: window.__explainer.cut.playing }));
  check(`${label}: cut-away play, pause and scrubber`, t2c.playing && t2c.t !== t1c && !t3c.playing && Math.abs(t3c.t - 1.0) < 0.01, `t ${t1c.toFixed(2)} -> ${t2c.t.toFixed(2)} s; scrub to ${t3c.t.toFixed(2)} s`);

  /* ---------------- section screenshots (animations paused) ---------------- */
  await pauseAll(page, true);
  for (const [name, sel] of SECTIONS) {
    const el = await page.$(sel);
    if (!el) { check(`${label}: section ${name} present`, false); continue; }
    await show(page, sel); await page.waitForTimeout(500);
    await el.screenshot({ path: path.join(SHOTS, `${label}_${name}.png`), timeout: 60000 });
  }
  await shot(page, "#known figure.slfig", `${label}_sideload.png`);

  /* ---------------- the 3-D pen ---------------- */
  await show(page, "#pen"); await page.waitForTimeout(400);
  const mv = await page.evaluate(() => { const H = window.__explainer.hero, c = getComputedStyle(document.documentElement).getPropertyValue("--g-nose").trim();
    const m = H.pen.parts.find(x => x.userData.id === "carrier"); return { mode: H.colorMode, key: document.querySelectorAll("#movekey li").length, legendHidden: document.getElementById("legend-wrap").hidden,
      col: m ? "#" + m.material.color.getHexString() : null, want: c }; });
  check(`${label}: 3-D colours show what moves by default (inner pen blue)`, mv.mode === "moves" && mv.key >= 5 && mv.legendHidden && mv.col && mv.col.toLowerCase() === mv.want.toLowerCase(),
    `${mv.key} kinds of motion; carrier ${mv.col} (inner pen ${mv.want})`);
  await page.click("#col-groups"); await page.waitForTimeout(250);
  const nLegend = await page.$$eval("#legend li", l => l.length);
  check(`${label}: part-group colours and legend`, nLegend >= 10, `${nLegend} groups`);
  await page.click("#legend li[data-group='power'] button.pick").catch(() => {});
  await page.waitForTimeout(300);
  const sel1 = await page.textContent("#info-name");
  check(`${label}: legend click selects a group`, /Battery|cell/i.test(sel1), sel1);
  await page.click("#col-moves"); await page.waitForTimeout(200);
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
  await page.click(".pin[data-act='tail']").catch(() => {}); await page.waitForTimeout(300);
  const selTail = await page.evaluate(() => ({ g: (window.__explainer.hero.sel || {}).group, txt: (document.getElementById("info") || document.getElementById("info-name").parentElement).textContent.replace(/\s+/g, " ") }));
  check(`${label}: the tail pin describes Rev J.1's lighter end-cap (optional), not the first design's 8–20 %`,
    selTail.g === "inertial" && /Rev J\.1/.test(selTail.txt) && /17\.3\s*g/.test(selTail.txt) && /optional/.test(selTail.txt) && !/8–20/.test(selTail.txt), selTail.txt.slice(0, 120));
  /* hand shake: the root moves along the paper while the ball stays */
  const ballRest = await page.evaluate(() => { const b = window.__explainer.hero.pen.ballWorld(); return [b.x, b.y, b.z]; });
  await page.click("#shake");
  const shk = await page.evaluate(async () => { const H = window.__explainer.hero, P = H.pen; let rootMax = 0, ballMax = 0, slugMax = 0;
    const b0 = P.ballWorld().clone(); const r0 = new THREE.Vector3().setFromMatrixPosition(P.root.matrix);
    for (let i = 0; i < 24; i++) { H.shakeT = i / 24 / 0.5; H.applyPose(); const b = P.ballWorld(), r = new THREE.Vector3().setFromMatrixPosition(P.root.matrix);
      rootMax = Math.max(rootMax, r.distanceTo(r0)); ballMax = Math.max(ballMax, b.distanceTo(b0)); slugMax = Math.max(slugMax, Math.abs(P.slug.position.y)); }
    return { rootMax, ballMax, slugMax, chip: !document.getElementById("hero-shake").hidden, pressed: document.getElementById("shake").getAttribute("aria-pressed") }; });
  await page.waitForTimeout(700);
  await shot(page, "#hero-vp", `${label}_pen_handshake.png`);
  check(`${label}: 3-D hand shake: the handle and hand move, the ball stays, the tail weight moves`, shk.pressed === "true" && shk.chip && shk.rootMax > 3 && shk.ballMax < 0.05 && shk.slugMax > 1,
    `handle moves ${shk.rootMax.toFixed(1)} mm, ball ${shk.ballMax.toFixed(3)} mm, tail weight ${shk.slugMax.toFixed(1)} mm`);
  await page.click("#shake"); await page.waitForTimeout(300);
  const ballBack = await page.evaluate(() => { const b = window.__explainer.hero.pen.ballWorld(); return [b.x, b.y, b.z]; });
  check(`${label}: hand shake off puts the pen back`, Math.hypot(ballBack[0] - ballRest[0], ballBack[1] - ballRest[1], ballBack[2] - ballRest[2]) < 0.05);
  await page.$eval("#explode", el => { el.value = "100"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.waitForFunction(() => window.__explainer.hero.explode > 0.9, null, { timeout: 8000 }).catch(() => {});
  const ex = await page.evaluate(() => window.__explainer.hero.explode);
  check(`${label}: "Take apart" separates the parts`, ex > 0.9, `explode ${ex.toFixed(2)}`);
  await shot(page, "#hero-vp", `${label}_pen_exploded.png`);
  await page.$eval("#explode", el => { el.value = "0"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.waitForFunction(() => window.__explainer.hero.explode < 0.02, null, { timeout: 8000 }).catch(() => {});
  await page.click("#xray"); await page.waitForTimeout(300);
  const xr = await page.evaluate(() => window.__explainer.hero.xray);
  check(`${label}: X-ray toggles`, xr === false);
  await page.click("#xray");
  await page.click("#endcap"); await page.waitForTimeout(300);
  const ec0 = await page.evaluate(() => { const P = window.__explainer.hero.pen; return { on: P.endcap, ec: P.parts.filter(m => m.userData.group === "inertial").some(m => m.visible),
    cap: P.parts.filter(m => m.userData.comp.replaced_by_endcap).every(m => m.visible), len: P.length(), pressed: document.getElementById("endcap").getAttribute("aria-pressed") }; });
  await shot(page, "#hero-vp", `${label}_pen_no_endcap.png`);
  await page.click("#endcap"); await page.waitForTimeout(300);
  const ec1 = await page.evaluate(() => { const P = window.__explainer.hero.pen; return { on: P.endcap, ec: P.parts.filter(m => m.userData.group === "inertial").every(m => m.visible), len: P.length() }; });
  check(`${label}: end-cap toggle (off: rear cap on; on: end-cap back)`, ec0.on === false && !ec0.ec && ec0.cap && ec0.pressed === "false" && ec1.on === true && ec1.ec && ec1.len > ec0.len,
    `off ${ec0.len.toFixed(1)} mm, on ${ec1.len.toFixed(1)} mm`);
  const rest = await page.evaluate(() => { const P = window.__explainer.hero.pen; return { z: P.refillG.position.z, psi: P.psi }; });
  await page.evaluate(() => window.__explainer.hero.padSet(45, 0));
  await page.waitForFunction(() => { const H = window.__explainer.hero; return Math.hypot(H.tip[0], H.tip[1]) > 3; }, null, { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(300);
  const moved = await page.evaluate(() => { const H = window.__explainer.hero, P = H.pen; return { tip: Math.hypot(H.tip[0], H.tip[1]), psi: P.psi, z: P.refillG.position.z, read: document.getElementById("pad-read").textContent }; });
  check(`${label}: tip pad swings the inner pen, slides the refill and steers the heel wheel`,
    moved.tip > 3 && Math.abs(moved.z - rest.z) > 0.05 && Math.abs(moved.psi - rest.psi) > 0.3,
    `tip ${moved.tip.toFixed(2)} mm; refill slid ${(moved.z - rest.z).toFixed(2)} mm; wheel turned ${(Math.abs(moved.psi - rest.psi) * 180 / Math.PI).toFixed(0)}°; "${moved.read}"`);
  await page.click("#cam-tip"); await page.waitForTimeout(700);
  await shot(page, "#hero-vp", `${label}_pen_tip_heel.png`);
  const pinsTip = await page.evaluate(() => window.__explainer.hero.pinsShown());
  await page.click("#cam-tail"); await page.waitForTimeout(700);
  await shot(page, "#hero-vp", `${label}_pen_tail.png`);
  const pinsTail = await page.evaluate(() => window.__explainer.hero.pinsShown());
  check(`${label}: camera views (tip and heel; tail)`, pinsTip.includes("heel") && pinsTip.includes("tip") && pinsTail.join() === "tail", `tip view pins ${pinsTip.join("+")}; tail view pins ${pinsTail.join("+")}`);
  await page.click("#cam-side"); await page.evaluate(() => window.__explainer.hero.padSet(0, 0));
  await page.waitForTimeout(600);

  /* ---------------- Details ---------------- */
  for (const id of DETAILS) { if (id === "d-scenes") continue;
    await openDet(page, id, true); await page.waitForTimeout(id === "d-results" ? 600 : 300);
    await show(page, "#" + id); await page.waitForTimeout(300);
    await shot(page, "#" + id, `${label}_${id}.png`);
  }
  const ph = await page.evaluate(() => ({ p: window.__explainer.physics, minis: window.__explainer.minis }));
  check(`${label}: Details: physics chart (tail weight, heel wheel) and mode pictures drawn`, ph.p && ph.p.points >= 5 && ph.p.traction >= 2 && ph.minis >= 15,
    `${ph.p ? ph.p.points : 0} points, ${ph.p ? ph.p.traction : 0} friction values, ${ph.minis} mode marks`);
  const comp = await page.$$eval("table.comp tbody tr", l => l.length);
  check(`${label}: Details: every part listed`, comp >= 40, `${comp} parts`);
  const lim = await page.$eval("#d-limits", el => el.textContent.replace(/\s+/g, " "));
  check(`${label}: Details: the corrected simulator check and the detent source`, /all 56/.test(lim) && /52 of 56/.test(lim) && /50 of 56/.test(lim) && /nose's magnet cap/.test(lim) && /0\.16/.test(lim),
    "3.1 % in all 56; 52 of 56; 50 of 56; detent from the nose's magnet cap");
  const resRows = await page.$$eval("table.res tbody tr", l => l.map(r => r.textContent.replace(/\s+/g, " ")));
  const trRow = resRows.find(r => /Tracing/.test(r)) || "";
  check(`${label}: Details: results table (${resRows.length} rows), tracing shown with the fall in letters read`, resRows.length >= 9 && /582/.test(trRow) && /76 µm/.test(trRow) && /92 %/.test(trRow) && /79 %/.test(trRow),
    trRow.slice(0, 120));
  const j1Row = resRows.find(r => /Rev J\.1's lighter end-cap/.test(r)) || "", firstRow = resRows.find(r => /first end-cap design \(superseded\)/.test(r)) || "";
  check(`${label}: Details: the tail rows: Rev J.1 (5.6 / 16.8 / 18.3 %, locked 12.6 / 11.1 / 6.7 %) and the first design's 8 / 18 / 20 %, marked superseded`,
    /5\.6 \/ 16\.8 \/ 18\.3/.test(j1Row) && /12\.6 \/ 11\.1 \/ 6\.7/.test(j1Row) && /8 \/ 18 \/ 20/.test(firstRow), `${j1Row.slice(0, 70)}… | ${firstRow.slice(0, 50)}…`);
  const panels = await page.$$eval("#results-body .rpanel", l => l.length);
  const conds = await page.$$eval("#results-body .rgroup", l => l.map(g => g.dataset.cond));
  check(`${label}: Details: handwriting strips render (tremor, autowrite, heel)`, panels >= 4 && ["tremor", "autowrite", "heel"].every(c => conds.includes(c)), `${panels} panels; groups ${conds.join(", ")}`);
  const w1 = await page.$eval(".strip svg", s => s.getBoundingClientRect().width);
  await page.click("[data-zoom='3']"); await page.waitForTimeout(200);
  const w3 = await page.$eval(".strip svg", s => s.getBoundingClientRect().width);
  check(`${label}: Details: "Magnified x3" enlarges the strips`, w3 > 2.5 * w1, `${w1.toFixed(0)} -> ${w3.toFixed(0)} px`);
  await page.click("[data-zoom='1']");

  /* the six scenes: built when their block is first opened */
  const before = await page.evaluate(() => !!window.__explainer.scenes);
  await openDet(page, "d-scenes", true);
  await page.waitForFunction(() => !!window.__explainer.scenes, null, { timeout: 30000 }).catch(() => {});
  const after = await page.evaluate(() => !!window.__explainer.scenes);
  check(`${label}: Details: the scenes are built only when opened`, !before && after);
  await show(page, "#d-scenes"); await page.waitForTimeout(600);
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
    if (k === "f") check(`${label}: scene f, the inner pen writes the letters (autowrite)`, st.noseMax > 2 && st.noseMax < 7.5, `largest offset ${st.noseMax.toFixed(2)} mm`);
    if (k === "e") {
      const ar = await page.evaluate(() => { const S = window.__explainer.scenes, was = S.playing; S.playing = false; S.seek(S.S.T * 0.4); const r = S.stats(); S.playing = was; return r; });
      await page.click("[data-writer='b']"); await page.waitForTimeout(250);
      const bs = await page.evaluate(() => { const S = window.__explainer.scenes, was = S.playing; S.playing = false; S.seek(S.S.T * 0.5); const r = S.stats(); S.playing = was; return r; });
      check(`${label}: scene e, the wheel pushes; a writer set on a 'b' keeps it`, ar.arrow && bs.bset && bs.arrow && bs.inkTriangles > 10, `push arrow ${ar.arrow}; 'b' writer ${bs.bset}`);
      await page.click("[data-writer='relaxed']"); await page.waitForTimeout(200);
      await page.evaluate(() => { const S = window.__explainer.scenes; S.seek(S.S.T * 0.8); });
    }
    await pauseAll(page, true); await page.waitForTimeout(200);
    await shot(page, ".scene-grid", `${label}_scene_${k}.png`);
    await pauseAll(page, false);
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
  await pauseAll(page, true);
  await show(page, "#d-scenes"); await page.waitForTimeout(400);
  await shot(page, "#d-scenes", `${label}_d-scenes.png`);

  const ov2 = await noScroll(page);
  check(`${label}: still no horizontal page scroll after interaction (all Details open)`, ov2[0] <= ov2[1], `scrollWidth ${ov2[0]} / viewport ${ov2[1]}`);
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
    /* dark theme: one look at the simple view and two Details blocks */
    const ctx = await browser.newContext({ viewport: { width: 1360, height: 900 }, colorScheme: "dark" });
    const p = await ctx.newPage();
    const derr = [];
    p.on("pageerror", e => derr.push(e.message));
    await p.goto(URL, { waitUntil: "load" });
    await p.waitForFunction(() => window.__explainer && window.__explainer.ready, null, { timeout: 60000 });
    await p.waitForTimeout(1500);
    await pauseAll(p, true);
    await openDet(p, "d-results", true); await openDet(p, "d-physics", true);
    for (const [name, sel] of [["top", "header.top"], ["moves", "#moves"], ["see", "#see"], ["pen", "#pen"], ["better", "#better"], ["sure", "#sure"], ["known", "#known"], ["d-physics", "#d-physics"], ["d-results", "#d-results"]]) {
      await show(p, sel); await p.waitForTimeout(500); await shot(p, sel, `dark_${name}.png`); }
    const bg = await p.evaluate(() => getComputedStyle(document.body).backgroundColor);
    check("dark theme: dark background and no page errors", derr.length === 0 && /rgb\(15, 18, 20\)/.test(bg), `${bg}; ${derr.slice(0, 3).join(" | ")}`);
    await ctx.close();
  } catch (e) { check("test run", false, e.message); }
  await browser.close();
  const failed = results.filter(r => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed; screenshots in ${SHOTS}`);
  process.exit(failed.length ? 1 : 0);
})();
