"""Reproducible mechanics improvement study; preserves historical results.

Run: python -m revk.improve [--quick] [--out results/improvement/mechanics]
The quick run is a diagnostic, not the reported numerical study.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess

import numpy as np

from .feasibility import (CoilShape, electrical_allocation, harmonic_force_rms,
                          thrust_guide, winding_map, wire_anchor)


ROOT = Path(__file__).resolve().parents[1]


def clean(x):
    if isinstance(x,float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, np.generic):
        return clean(x.item())
    return x


def disk_samples(radius, n=16):
    a = np.arange(n) * 2 * math.pi / n
    ring = np.column_stack([np.cos(a), np.sin(a)])
    return np.vstack([np.zeros((1, 2)), ring * radius * .5, ring * radius])


def guide_geometry(radius_mm, body_od_mm=24., wire_d_mm=.1):
    """Conservative complete-ring guide bounds, including half-speed ball rolling.

    New guides require displaced coil/hall lead routing and a separately checked
    counter-face. The bore check is necessary, not proof of whole-device fit.
    """
    stop = radius_mm + .2
    bore = body_od_mm / 2 - 1.
    flange_r = bore - stop - .3
    ball_circle = flange_r - stop / 2 - .4 - .2
    race_width = stop + .8 + .4
    race_inner = ball_circle - race_width / 2
    wire_r_max = race_inner - stop - wire_d_mm / 2 - .3
    wire_r_min = 1.175 + stop + .3 + .3  # refill swept envelope + clearance + clamp
    return {"radius_mm": radius_mm, "stop_mm": stop, "body_od_mm": body_od_mm,
            "bore_radius_mm": bore, "flange_radius_mm": flange_r,
            "ball_circle_radius_mm": ball_circle, "race_width_mm": race_width,
            "race_inner_radius_mm": race_inner, "wire_circle_min_mm": wire_r_min,
            "wire_circle_max_mm": wire_r_max, "wire_circle_mm": (wire_r_min + wire_r_max) / 2,
            "guide_wire_fit": wire_r_max >= wire_r_min,
            "minimum_body_od_mm": 2 * (4 * stop + 3.625 + 1),
            "limitation": "full circular races + rearward straight wire leads; different guide topology may change bound"}


def search_coil(radius_mm, body_od_mm=24., quick=False):
    from .nib import chk_geom
    bore = body_od_mm / 2 - 1
    stop = (radius_mm + .2) * 1e-3
    rmax = bore * 1e-3 - stop - .3e-3
    # Keep stator inside bore, expand the refill opening with the new stop.
    g = chk_geom()
    e = (1.6e-3 + stop + .3e-3) / math.sqrt(2)
    w = min(g.w, (bore - .6) * 1e-3 / math.sqrt(2) - e)
    g = replace(g, e=e, w=w, s=stop)
    candidates = []
    for b in np.array([1.2, 1.7, 2.2, 2.6] if not quick else [1.7, 2.2]) * 1e-3:
        for yc in np.array([3.75, 4.25, 4.75, 5.25] if not quick else [4.25, 4.75]) * 1e-3:
            for xi in np.array([1.8, 2.2, 2.6] if not quick else [2.2]) * 1e-3:
                if xi + b >= rmax:
                    continue
                yi = min(math.sqrt(rmax ** 2 - (xi + b) ** 2) - yc - b, yc - b - 1.7e-3)
                if yi < .15e-3:
                    continue
                s = CoilShape(xi, yi, b, yc)
                m = winding_map(g, s, np.zeros((1, 2)), "xyyx", quadrature=(2, 1, 6))
                candidates.append((float(m["min_singular_N_sqrtW"][0]), s))
    candidates.sort(key=lambda x: -x[0])
    if not candidates:
        return {"feasible_geometry": False, "reason": "no winding clears carrier and circular bore"}
    keep = candidates[:(2 if quick else 6)]
    best = None
    for _, shape in keep:
        for order in ("xy", "xyyx", "yxxy"):
            m = winding_map(g, shape, disk_samples(radius_mm * 1e-3, 8), order, quadrature=(2, 1, 8))
            score = float(m["min_singular_N_sqrtW"].min())
            if best is None or score > best[0]:
                best = (score, shape, order)
    _, shape, order = best
    m = winding_map(g, shape, disk_samples(radius_mm * 1e-3, 16 if quick else 48), order,
                    quadrature=(3, 2, 12) if quick else (5, 3, 24))
    return {"feasible_geometry": True, "shape_m": asdict(shape), "magnet_geometry_m": asdict(g),
            "order": order, "nominal_min_singular_N_sqrtW": float(m["min_singular_N_sqrtW"].min()),
            "centre_matrix_N_sqrtW": m["wrench_per_sqrtW"][0,:2,:],
            "map": m, "candidate_count": len(candidates),
            "coil_bore_clearance_at_stop_mm": (bore * 1e-3 - shape.outer_radius - stop) * 1e3,
            "copper_mass_g": float(m["copper_mass_kg"].sum()) * 1e3,
            "magnet_mass_g": 4 * w * w * g.t_m * 7500 * 1e3,
            "selection": "maximize minimum singular value on sampled mechanical disk, then refine field quadrature"}


def wire_design(radius_mm, n_wires=8):
    """Shortest lead suspension meeting conservative dimensional corner SF >=1.6.

    Extending wires also extends the refill holder/head and body; it is charged
    as a package change, never hidden inside the existing layout.
    """
    stop = (radius_mm + .2) * 1e-3
    for Lmm in [26.801, 28, 30, 32, 34, 36, 40, 45, 50]:
        for dmm in [.10]:
            r = wire_anchor(stop, length=Lmm * 1e-3 - .05e-3,
                            diameter=dmm * 1.02e-3, young=127.6e9 * 1.04,
                            anchor_stiffness=120., assembly_tension=.005, kt=2.5,n_wires=n_wires)
            if r["goodman_sf_conservative"] >= 1.6:
                rho = 1.7241e-8 / .22
                A = math.pi / 4 * (dmm * 1e-3) ** 2
                R = rho * Lmm * 1e-3 / A
                # Conservative no-convection wire between equal-temperature
                # clamps; T_mid-T_end = I_rms^2 rho L^2 /(8 k A^2).
                k_cond, delta_T = 105., 45.  # ASSUMPTIONS; coupon measurements required
                Iheat = math.sqrt(8 * k_cond * A ** 2 * delta_T / (rho * (Lmm * 1e-3) ** 2))
                return {"length_mm": Lmm, "diameter_mm": dmm,"n_wires":n_wires,"parallel_wires_per_lead":n_wires//4,
                        "holder_and_body_extension_mm": max(Lmm - 26.801, 0),
                        "anchor_stiffness_N_m": 100., "assembly_tension_max_N": .005,
                        "wire_resistance_20C_ohm": R, "wire_continuous_rms_current_A": Iheat,
                        "coil_continuous_rms_current_A_from_parallel_leads":Iheat*(n_wires//4),
                        "wire_thermal_assumptions": {"conductivity_W_mK": k_cond, "rise_above_clamps_K": delta_T,
                            "clamp_temperature_unknown": True}, "worst_corner": r,
                        "status": "CALC target; wire diameter/length/E/anchor corners, Kt2.5, fatigue factor0.85"}
    return {"feasible": False, "reason": "fatigue target not met within50mm wire length"}


def matched_force_duty(coil, wire, radius_mm, field_scale=.7, residual_N=.04):
    """Transparent periodic force feasibility, including lead Joule heat.

    residual_N bundles contact/balance/guide loads as an explicit sensitivity
    input. It is not a measured universal load. Test radius in8 directions at
    8Hz, actual matrix interpolated by nearest angular map sample at edge.
    """
    mp = coil["map"]
    maps = np.asarray(mp["wrench_per_sqrtW"])[:, :2, :] * field_scale
    positions = np.asarray(mp["positions_m"])
    mass = (.00349 + max(wire["holder_and_body_extension_mm"], 0) * .025e-3)
    rows = []
    L = wire["length_mm"] * 1e-3
    d = wire["diameter_mm"] * 1e-3
    rho = 1.7241e-8 / .22
    area = math.pi * d*d/4
    parallel = wire.get("parallel_wires_per_lead",1)
    Rlead = 2 * wire["wire_resistance_20C_ohm"] / parallel
    # Build a force-law interpolation once, not a nonlinear solve each tick.
    qq = np.linspace(0, radius_mm*1e-3, 101)
    ff = np.array([wire_anchor(q,length=L,diameter=d,anchor_stiffness=wire.get('anchor_stiffness_N_m',100.),
                             assembly_tension=wire.get('assembly_tension_max_N',.005),
                             n_wires=wire.get("n_wires",4))["lateral_force_N"] for q in qq])
    phase = np.linspace(0, 2*math.pi, 512, endpoint=False)
    for f in (4., 8., 12.):
        w = 2*math.pi*f
        for a in np.arange(8)*math.pi/4:
            direction = np.array([math.cos(a), math.sin(a)])
            qscalar = radius_mm*1e-3*np.sin(phase)
            q = qscalar[:,None]*direction
            velocity = radius_mm*1e-3*w*np.cos(phase)[:,None]*direction
            accel = -w*w*q
            spring = (np.sign(qscalar)*np.interp(np.abs(qscalar),qq,ff))[:,None]*direction
            force = mass*accel + spring + residual_N*direction
            idx = np.argmin(np.linalg.norm(positions[:,None,:]-q[None,:,:],axis=2),axis=0)
            kf = maps[idx]*math.sqrt(2.5)
            currents = np.linalg.solve(kf,force[...,None])[...,0]
            # Hot winding+leads for voltage and electrical power; thermal wire
            # estimate accounts for resistance temperature feedback separately.
            Rhot = (2.5+Rlead)*(1+.00393*90.)
            voltage = (Rhot+.24)*currents + np.einsum('nji,nj->ni', kf, velocity)
            rms = np.sqrt(np.mean(currents**2,axis=0))
            p = float(np.mean(np.sum(currents**2,axis=1))*Rhot)
            heat0 = (rms/parallel)**2*rho*L*L/(8*105.*area*area)
            # Steady hot resistivity positive feedback. Unknown clamp temperature
            # not added, so this is rise above the clamps, not absolute wire T.
            heat = np.divide(heat0,1-.00393*heat0,out=np.full_like(heat0,np.inf),where=1-.00393*heat0>0)
            rows.append({"frequency_Hz":f,"direction_deg":math.degrees(a),
                         "current_rms_A":rms,"current_peak_A":float(np.max(np.abs(currents))),
                         "voltage_peak_V":float(np.max(np.abs(voltage))),"copper_power_W":p,
                         "wire_rise_above_clamps_K":heat,
                         "wire_thermal_equilibrium_exists":bool(np.isfinite(heat).all()),
                         "electrical_pass":bool(np.max(np.abs(voltage))<=3.3 and np.max(np.abs(currents))<=1),
                         "wire_thermal_pass":bool(np.max(heat)<=45.),"coil_thermal_pass":bool(p<=.15)})
    return {"rows":rows,"field_scale":field_scale,"residual_load_N":residual_N,
            "moving_mass_kg":mass,"coil_limit_W_assumed":.15,
            "all_cases_pass":all(r['electrical_pass'] and r['wire_thermal_pass'] and r['coil_thermal_pass'] for r in rows),
            "limitations":"periodic prescribed motion, no tracking error or driver switching/inductance; residual force assumed"}


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--quick',action='store_true')
    ap.add_argument('--reuse-fields',action='store_true',help='reuse this study\'s existing magnetostatic maps only; recompute wire/load checks')
    ap.add_argument('--out',type=Path,default=ROOT/'results/improvement/mechanics')
    args=ap.parse_args(argv); args.out.mkdir(parents=True,exist_ok=True)
    from . import counterface, frontend, nib
    old=json.loads((ROOT/'results/revK/revK.json').read_text())
    oldc=old['nib']['buildable_coil']['geometry_mm']
    shape=CoilShape(oldc['X_in']*.001,oldc['Y_in']*.001,oldc['bundle_b']*.001,oldc['row_centre_yc']*.001)
    radius=1.058695965882101
    prior={}
    if args.reuse_fields and (args.out/'mechanics_study.json').exists():
        prior=json.loads((args.out/'mechanics_study.json').read_text())
    baseline_map=prior.get('baseline',{}).get('map') or winding_map(nib.chk_geom(),shape,disk_samples(radius*.001,48),'xy',quadrature=(5,3,24))
    oldrows={r['radius_mm']:r for r in prior.get('candidates',[])}
    before_wire=wire_anchor((radius+.2)*.001)
    after_wire=wire_anchor((radius+.2)*.001,anchor_stiffness=1000.)
    guide=thrust_guide([old['nib']['couple']['worst']['couple_mNm']*.001,0])
    study={"evidence_status":"CALCULATION on proposed design; nothing measured",
           "baseline":{"radius_mm":radius,"map":baseline_map,"original_anchor":before_wire,
                       "soft_anchor_same_wires":after_wire,"preloaded_guide":guide},"candidates":[]}
    baseline_wire={'length_mm':26.801041139863813,'diameter_mm':.1,'n_wires':4,'parallel_wires_per_lead':1,
                   'holder_and_body_extension_mm':0.,'anchor_stiffness_N_m':10000.,'assembly_tension_max_N':.005,
                   'wire_resistance_20C_ohm':(1.7241e-8/.22)*.026801041139863813/(math.pi*(.0001)**2/4)}
    study['baseline']['matched_wire_inputs']=baseline_wire
    study['baseline']['matched_duty_by_residual']={str(load):matched_force_duty({'map':baseline_map},baseline_wire,radius,residual_N=load)
                                                  for load in (.02,.04,.08)}
    for t in (radius,1.5,2.,2.5,3.):
        body=24.
        geom=guide_geometry(t,body)
        print(f'[{t:.3f}mm] magnetics and constraints',flush=True)
        cached=oldrows.get(t,{})
        coil=cached.get('coil') or search_coil(t,body,args.quick)
        wire=wire_design(t)
        # Counter-face/free space evaluated even when a guide constraint fails.
        front=cached.get('front_end') or frontend.front_close(quick=True,travel=t,stop=t+.2)
        head={'chosen':cached['head'],'rows':[None]*cached['head_candidate_count']} if 'head' in cached else counterface.sweep(front['R_s_mm'],quick=args.quick,stop_mm=t+.2)
        row={"radius_mm":t,"geometry":geom,"coil":coil,"wire":wire,
             "front_end":front,"head":head['chosen'],"head_candidate_count":len(head['rows']),
             "limit_reasons":[]}
        if not geom['guide_wire_fit']: row['limit_reasons'].append('circular race vs wire-anchor/refill swept envelope')
        if head['chosen'] is None: row['limit_reasons'].append('counter-face does not fit')
        if not coil['feasible_geometry']: row['limit_reasons'].append('no buildable winding')
        if coil['feasible_geometry'] and 'length_mm' in wire:
            row['duty_by_residual']={str(load):matched_force_duty(coil,wire,t,residual_N=load) for load in (.02,.04,.08)}
            row['conservative_duty_pass']=row['duty_by_residual']['0.04']['all_cases_pass']
            if not row['conservative_duty_pass']: row['limit_reasons'].append('0.04N residual full-radius4–12Hz duty exceeds an electrical/heat limit')
        row['geometry_candidate']=not any('race' in s or 'face' in s or 'winding' in s for s in row['limit_reasons'])
        study['candidates'].append(row)
        (args.out/'mechanics_study.json').write_text(json.dumps(clean(study),indent=2)+'\n')
        print(f"  geometry={row['geometry_candidate']} minKm={coil.get('nominal_min_singular_N_sqrtW',0):.4f} limits={row['limit_reasons']}",flush=True)
    study['provenance']={"git":subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                         "python":platform.python_version(),"platform":platform.platform(),"quick":args.quick,
                         "reused_magnetostatic_fields":args.reuse_fields,
                         "sources_sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [ROOT/'revk/feasibility.py',ROOT/'revk/improve.py',ROOT/'results/revK/revK.json']}}
    (args.out/'mechanics_study.json').write_text(json.dumps(clean(study),indent=2)+'\n')
    print(args.out/'mechanics_study.json',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
