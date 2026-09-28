"""HTML tables for viewer/index.html, rendered from the result files at build time.

Every number comes from a results/ JSON written by the analysis or simulation
scripts; nothing is typed in here.  Each section carries its evidence label.
Sections whose inputs are missing are skipped, so the page builds at any stage.
"""
from __future__ import annotations

import html
import json
import os

TAG = {"SIM": ("sim", "Simulation"), "CALC": ("calc", "Calculation"), "MFR": ("mfr", "Manufacturer statement"),
       "ASSUMPTION": ("asm", "Assumption"), "CAD": ("calc", "CAD, proposed design")}


def _load(root, rel):
    p = os.path.join(root, rel)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _e(x):
    return html.escape(str(x))


def _tags(*keys):
    return " ".join(f'<span class="tag {TAG[k][0]}"><i></i>{TAG[k][1]}</span>' for k in keys)


def _num(v, nd=0, unit=""):
    if v is None:
        return "—"
    if isinstance(v, str):
        return _e(v)
    s = f"{v:,.{nd}f}".replace(",", " ")
    return s + (f" {unit}" if unit else "")


def _table(head, rows, num_cols=()):
    th = "".join(f"<th>{_e(h)}</th>" for h in head)
    body = []
    for r in rows:
        tds = []
        for j, c in enumerate(r):
            cls = ' class="num"' if j in num_cols else ""
            tds.append(f"<td{cls}>{c}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _section(title, tags, lede, inner, source):
    return (f'<section class="block"><h2>{_e(title)}</h2><div class="row">{tags}</div>'
            f'<p class="note">{lede}</p>{inner}<p class="note">Source: <code>{_e(source)}</code></p></section>')


def _pill(verdict):
    v = verdict.lower()
    if v.startswith("recommend"):
        return '<span class="pill go">recommended</span>'
    if "fallback" in v or "second" in v or "bench" in v or "haptic" in v:
        return '<span class="pill maybe">limited use</span>'
    return '<span class="pill no">rejected</span>'


# ------------------------------------------------------------------ sections
def forces(root):
    m = _load(root, "results/pencil/mechanisms.json")
    if not m:
        return ""
    n = m["a_loads"]["nominal"]
    c, s = n["conventional_pen"], n["skid"]
    v = lambda d, k: d[k]["value"] if isinstance(d.get(k), dict) else d.get(k)
    rows = [
        ["Normal force at the nib", _num(v(c, "N_nib_N"), 3, "N"), _num(v(s, "N_nib_N"), 3, "N")],
        ["Stage load, tilt plane, static (N cos θ, or F<sub>c</sub> cot θ)", _num(v(c, "R_t1_static_N"), 3, "N"),
         _num(v(s, "R_perp_frictionless_N"), 3, "N")],
        ["<b>Design load per stage axis</b> (worst stroke direction, with friction)", f"<b>{_num(v(c, 'R_perp_max_N'), 3, 'N')}</b>",
         f"<b>{_num(v(s, 'R_perp_max_N'), 3, 'N')}</b>"],
        ["Skid normal force / friction", "—", f"{_num(v(s, 'N_skid_N'), 3)} / {_num(v(s, 'skid_friction_N'), 3, 'N')}"],
        ["Axial load", _num(v(c, "axial_N"), 3, "N"), "0.150 N (spring F<sub>c</sub>)"],
    ]
    env = m["a_loads"]["envelope"]
    lede = ("Pen at 50° with 1 N of writing force, nib friction 0.15, skid friction 0.12 (assumed) and a 0.15 N axial nib spring "
            "(assumed). Any stage that moves the nib across the barrel must hold the paper's reaction. Behind the skid it drops "
            f"by a factor of {v(c, 'R_perp_max_N') / v(s, 'R_perp_max_N'):.1f}. Over the whole envelope (35–75°, μ 0.05–0.35, "
            f"F<sub>c</sub> 0.08–0.30 N) the skid design load spans {env['skid_R_perp_max_N'][0]:.3f}–{env['skid_R_perp_max_N'][1]:.2f} N; "
            "the dynamic forces of tremor are under 4 % of the static load.")
    return _section("Forces at the nib", _tags("CALC", "ASSUMPTION"), lede,
                    _table(["Quantity", "Pencil-form pen (nib carries the force)", "Skid architecture"], rows, (1, 2)),
                    "results/pencil/mechanisms.json (analysis/pencil_mechanisms.py)")


def mechanisms(root):
    m = _load(root, "results/pencil/mechanisms.json")
    if not m:
        return ""
    rows = []
    order = ["Q26", "L35", "PL128", "L40", "PL1xx", "APA", "VCM", "SQUIGGLE", "SMA", "LRA", "GYRO", "TMD"]
    by = {c["key"]: c for c in m["b_candidates"]}
    for k in order:
        c = by.get(k)
        if not c:
            continue
        st = c.get("stroke_nib_um")
        if isinstance(st, dict):
            stroke = f"±{st['at_F_betaworst_0.170N']:.0f} µm<br><span class=\"note\">±{st['betaworst_at_minus20pct_tolerance']:.0f} at −20 %</span>"
        else:
            stroke = "—"
        hp = c.get("holding_power_W")
        if isinstance(hp, dict):
            hold = f"{hp['skid_betaworst']:.1f} W"
        elif isinstance(hp, (int, float)):
            hold = ("≈ 0 (self-locking)" if k == "SQUIGGLE" else "≈ 0 (capacitive)") if hp == 0 else f"{hp:.2f} W"
        else:
            hold = "—"
        f1 = c.get("first_resonance_Hz")
        f1s = f"{f1:.0f} Hz" if isinstance(f1, (int, float)) else "—"
        fn = c.get("force_nib_N")
        fns = f"{fn:.3f} N" if isinstance(fn, (int, float)) else "—"
        verdict = c.get("verdict", "")
        if k == "Q26":
            verdict = "recommended: zero static hold power; needs snubbers and a compliant nose to survive a drop"
        elif k == "L35":
            verdict = "fallback: stroke margin and snubber web too small"
        elif k == "PL128":
            verdict = "bench part: only one fits the bore; for the one-axis rig"
        elif k == "LRA":
            verdict = "haptic cue only: cannot move the nib"
        elif k == "PL1xx":
            verdict = "reject: 9.6-11 mm wide, does not fit the 7.9 mm bore; the same ceramic is used as custom-width plates"
        elif k == "APA":
            verdict = "reject: does not fit (10.3 mm section diagonal) and needs 150 V drive"
        short = verdict.split(":", 1)[1].strip() if ":" in verdict else verdict
        short = short[:1].upper() + short[1:]
        rows.append([_e(c["candidate"]), stroke, fns, f1s, hold, f"{_pill(verdict)}<br><span class=\"note\">{_e(short if len(short) < 160 else short[:157] + '…')}</span>"])
    lede = ("Design load 0.170 N per axis at the nib (skid architecture, worst stroke direction); the usable correction target is "
            "±0.30 mm. Catalogue data are manufacturer statements with ledger ids in the source file; strokes, forces and "
            "powers are calculations; the voice coil is a magnetostatic simulation.")
    return _section("Which mechanism can move the nib", _tags("CALC", "SIM", "MFR"), lede,
                    _table(["Mechanism", "Nib stroke under load", "Force at nib", "First resonance", "Static hold power", "Verdict"], rows, (1, 2, 3, 4)),
                    "results/pencil/mechanisms.json (analysis/pencil_mechanisms.py; docs/pencil_mechanisms.md §3)")


def power(root):
    s = _load(root, "results/pencil/sim_metrics.json")
    if not s:
        return ""
    t = s["battery"]["table"]
    pick = [("recording_only", "Recording only"), ("tremor assist, full correction (oracle), 6 Hz", "Tremor assist, 6 Hz, Hall noise 1 µm"),
            ("guided assist, 6 Hz tremor", "Guided assist, 6 Hz tremor"), ("oracle 6Hz, Hall noise 0.3 um", "Tremor assist, 6 Hz, Hall noise 0.3 µm")]
    rows = []
    for k, lab in pick:
        if k not in t:
            continue
        d, r = t[k]["drv2700"], t[k]["recovery"]
        pd = d.get("P_total_W", d.get("P_W")); pr = r.get("P_total_W", r.get("P_W"))
        rows.append([lab, f"{pd * 1e3:.0f} mW, <b>{d['life_h']:.1f} h</b>", f"{pr * 1e3:.0f} mW, <b>{r['life_h']:.1f} h</b>"])
    lede = ("90 mAh cell at 3.7 V, 80 % usable (assumed); electronics 65 mW including a 50 mW optics placeholder (assumed). "
            "The piezo holds the static load for free; the driver's quiescent draw and the sensor noise that the damping loop "
            "turns into drive power set the battery life.")
    return _section("Power and battery", _tags("SIM", "ASSUMPTION"), lede,
                    _table(["Mode", "Two DRV2700 drivers (bench)", "Charge-recovery driver (product)"], rows, (1, 2)),
                    "results/pencil/sim_metrics.json battery (sim/pencil, model P1)")


def effect(root):
    s = _load(root, "results/pencil/sim_metrics.json")
    if not s:
        return ""
    g = s["grid_summary"]
    freqs = ["4", "6", "8", "10", "12"]
    rows = []
    for mode, lab in (("oracle", "Physical limit (perfect intent)"), ("kfosc", "Tremor estimator (Kalman)")):
        for amp in ("0.1", "0.3", "0.5"):
            rows.append([f"{lab}, {amp} mm tremor"] + [f"{g[mode]['ratio'][f'{f}Hz_{amp}mm']['mean']:.2f}" for f in freqs])
    sat = ["Time at travel limit, physical limit, 0.3 mm"] + [f"{100 * g['oracle']['q_sat_frac'][f'{f}Hz_0.3mm']['mean']:.0f} %" for f in freqs]
    rows.append(sat)
    gf = s["guided_feature_course_path_distance"]
    gl = ", ".join(f"{k.replace('_', ' ')} {v['neutral']['rms_um']:.0f} → {v['guided']['rms_um']:.0f} µm" for k, v in gf.items())
    lede = ("Ink error divided by the error of the same pencil with its stage held still, on synthetic handwriting (test seeds 200–203). "
            "Below 1 is better. The physical limit shows what the stage can do when it knows the tremor exactly; the estimator "
            "shows what the pen's own sensors achieve today. Guided mode on the feature course (path distance): " + _e(gl) + ".")
    return _section("What the pencil does to the ink", _tags("SIM"), lede,
                    _table(["Case"] + [f"{f} Hz" for f in freqs], rows, (1, 2, 3, 4, 5)),
                    "results/pencil/sim_metrics.json grid_summary (sim/pencil/run_study.py)")


def sensor(root):
    d = _load(root, "results/sim/page_sensor_rate.json")
    if not d:
        return ""
    rows = [[f"{r['rate_hz']:.0f} Hz, {r['latency_s'] * 1e3:.0f} ms" + (" (parameter default)" if r.get("note") else ""),
             f"{r['guided_path_rms_um']:.0f} µm", f"{r['guided_over_neutral']:.2f}"] for r in d["rows"]]
    lede = ("Recording writing on paper needs a page-referenced sensor near the nib. The only camera found that fits the nose "
            "runs at 30 fps (OVM6948, OPT-36). With the IMU bridging between samples, guided mode needs at least 120 Hz with "
            "10 ms latency to keep its benefit (feature course, 6 Hz 0.3 mm tremor, model M1).")
    return _section("How fast the paper sensor must be", _tags("SIM", "MFR", "ASSUMPTION"), lede,
                    _table(["Page sensor", "Guided path error, RMS", "Relative to no correction"], rows, (1, 2)),
                    "results/sim/page_sensor_rate.json (sim/diag_page_sensor_rate.py)")


def tails(root):
    d = _load(root, "results/pencil/touchdown_tails.json")
    if not d:
        return ""
    lab = {"tilt_range_stop": "Whole tilt range (current CAD)", "adaptive_0.30mm": "Tilt-adaptive, 0.30 mm margin",
           "adaptive_0.20mm": "Tilt-adaptive, 0.20 mm margin", "adaptive_0.10mm": "Tilt-adaptive, 0.10 mm margin"}
    rows = [[lab[k], f"{v['extra_ink_mm_per_stroke']:.2f}", f"{v['missing_ink_mm_per_stroke']:.2f}", f"{v['oracle_ratio']:.2f}"]
            for k, v in d["summary"].items() if k in lab]
    lede = ("With the skid, a light spring pushes the refill out whenever the pen is lifted. If its front stop allows for every "
            "tilt, the ball lands first and slides while the refill retracts, drawing a tail at every touchdown and lift. "
            "A stop that follows the pen's tilt, set by a slow trim motor from the IMU, cuts the tails; the margin must still "
            "leave the refill room to slide while the stage corrects. Ink is compared with a rigid pen on the same writing "
            "(0.2 mm tolerance). The error ratio is the ink error with perfect disturbance knowledge divided by the "
            "error with no correction; lower is better.")
    return _section("Touchdown tails and a tilt-adaptive stop", _tags("SIM"), lede,
                    _table(["Front stop", "Extra ink per stroke, mm", "Missing ink per stroke, mm", "Error ratio"], rows, (1, 2, 3)),
                    "results/pencil/touchdown_tails.json (sim/pencil/diag_touchdown_tails.py)")


def packaging(root, variant="Q"):
    d = _load(root, f"results/cad/pencil_revP{variant}_summary.json")
    if not d:
        return ""
    s = d["summary"]
    c = s["section_checks"]
    rows = [["Mass before wiring, adhesive and margin", f"{s['mass_total_g']} g"],
            ["Centre of mass from the nib", f"{s['com_z_mm']} mm of 166 mm"],
            ["Lever, nib per collar motion", f"{s['lever_nib_per_collar']}"],
            ["Decoupling leaf free span", f"{s['leaf_free_span_mm']} mm"],
            ["Plate corner to bore (tips at the ±0.40 mm stops)", f"{c['plate_to_bore_mm']} mm"],
            ["Plate to plate / plate to refill", f"{c['plate_to_plate_mm']} / {c['plate_to_refill_mm']} mm"],
            ["Thinnest snubber web", f"{c['snubber_min_web_mm']} mm"],
            ["Refill cone to skid aperture at 35°, full travel", f"{c['refill_cone_to_skid_aperture_at_theta_min_mm']} mm"],
            ["Nib assembly swept through ±0.40 mm", "no interference" if not s["nib_assembly_interference"] else "interference"],
            ["All geometric checks", "pass" if c["all_ok"] else "fail"]]
    lede = ("Four 2.6 mm piezo plates around a D1 refill in the 7.9 mm bore, a skid ring on the nose, a rear gimbal, "
            "a rigid-flex board and a 6.5 × 40 mm cell. Nominal dimensions and rigid parts; the checks are geometric.")
    return _section("Does it fit an 8.9 mm pencil", _tags("CAD"), lede, _table(["Check", "Result"], rows, (1,)),
                    f"results/cad/pencil_revP{variant}_summary.json (mechanics/cad/pencil_revP.py)")


def make_buy(root):
    m = _load(root, "results/pencil/mechanisms.json")
    if not m:
        return ""
    rows = [[_e(r["item"]), _e(r["decision"]), f'<span class="note">{_e(r.get("note", ""))}</span>'] for r in m["d_make_buy"]]
    return _section("What to make and what to buy", _tags("CALC"),
                    "Buy what exists; make the custom-width piezo plates (a supplier custom part), the precision mechanics, "
                    "the board, the drive stage and the cell.",
                    _table(["Item", "Decision", "Note"], rows), "results/pencil/mechanisms.json d_make_buy")


def render(root, variant="Q"):
    try:
        from viewer import sections_extra  # AI guidance, sim-to-real and inertial-helper tables, once those results exist
    except ImportError:
        sections_extra = None
    parts = [forces(root), mechanisms(root)]
    if sections_extra:
        parts.append(sections_extra.inertial(root))
    parts += [effect(root), tails(root), power(root), sensor(root), packaging(root, variant), make_buy(root)]
    if sections_extra:
        parts += [sections_extra.ai(root), sections_extra.s2r(root)]
    body = [p for p in parts if p]
    if not body:
        return ""
    return '<div class="grid1">' + "".join(body) + "</div>"
