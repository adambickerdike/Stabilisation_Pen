"""Actual20mm body compaction screen; never reuse24mm magnetic authority."""
from __future__ import annotations
import json
from pathlib import Path
import hashlib
from .improve import ROOT,clean,guide_geometry,search_coil,wire_design,matched_force_duty
from .feasibility import thrust_guide
from . import counterface,frontend


def main():
    out=ROOT/'results/improvement/mechanics';radius=1.058695965882101;body=20.
    geometry=guide_geometry(radius,body)
    front=frontend.front_close(quick=False,travel=radius,stop=radius+.2,body_od_mm=body)
    head_sweep=counterface.sweep(front['R_s_mm'],quick=False,stop_mm=radius+.2)
    head_limit=geometry['bore_radius_mm']-.3
    fit=[r for r in head_sweep['rows'] if r['keeps_spare_travel'] and r['swept_r_max_mm']<=head_limit]
    head=min(fit,key=lambda r:(r['plate_mm']['length'],r['follower_range_mm'])) if fit else None
    print('head candidates fitting20mm',len(fit),'/',len(head_sweep['rows']),flush=True)
    coil=search_coil(radius,body,quick=False)
    wire=wire_design(radius)
    old=json.loads((ROOT/'results/revK/revK.json').read_text())
    matched_moment=old['nib']['couple']['worst']['couple_mNm']*.001
    guide_load=thrust_guide([matched_moment,0],circle_radius=geometry['ball_circle_radius_mm']*.001)
    # Resized coupon leaves0.3mm outer ring and0.35mm wire-pad land. Target
    # beam stiffness76.6N/m leaves23.4N/m nominal for cable/other contributions.
    hub=geometry['wire_circle_mm']+.35
    beam_length=(geometry['bore_radius_mm']-.3-hub)*.001
    beam_width=.0005;E=193e9;target=76.6
    thickness=(target*beam_length**3/(4*E*beam_width))**(1/3)
    result=dict(evidence='CALC20mm component compaction screen; not whole-pen or manufactured fit',
        radius_mm=radius,body_od_mm=body,geometry=geometry,front_end=front,
        counterface=dict(swept_radius_limit_mm=head_limit,fitting_count=len(fit),
                        searched_count=len(head_sweep['rows']),chosen=head,
                        minimum_swept_radius_with_spare_mm=min(r['swept_r_max_mm'] for r in head_sweep['rows'] if r['keeps_spare_travel'])),
        coil=coil,wire=wire,guide_load_screen=dict(applied_moment_Nm=matched_moment,
            provenance='Matched historical worst nib moment; not a complete new six-axis loaded guide envelope',
            result=guide_load),anchor_coupon=dict(beam_count=4,beam_length_mm=beam_length*1000,
            beam_width_mm=.5,required_beam_thickness_mm=thickness*1000,
            assumed_modulus_GPa=193.,target_beam_stiffness_N_m=target,
            nominal_flex_cable_allowance_N_m=100.-target,status='calculated target, processing and cable unknown'),
        limit_reasons=[],unresolved=['electronics/PCB/cell repackaging','head hinge and positioner solid envelopes',
                                    'coil former and winding manufacture','support stiffness and screw/adhesive joints',
                                    'full3D collision and assembly access'])
    if not geometry['guide_wire_fit']:result['limit_reasons'].append('guide/lead swept envelope')
    if head is None:result['limit_reasons'].append('no counter-face candidate clears resized bore with follower reserve')
    if not coil['feasible_geometry']:result['limit_reasons'].append('no winding candidate')
    else:
        result['duty_by_residual']={str(load):matched_force_duty(coil,wire,radius,residual_N=load) for load in [.02,.04,.08]}
        if not result['duty_by_residual']['0.04']['all_cases_pass']:
            result['limit_reasons'].append('40mN loaded full-radius4–12Hz electrical or thermal screen')
    result['component_geometry_screen_pass']=bool(geometry['guide_wire_fit'] and head is not None and coil['feasible_geometry'])
    result['whole_pen_feasibility']='UNRESOLVED; cannot infer full electronics/head fit from component screens'
    result['code_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),ROOT/'revk/improve.py',ROOT/'revk/feasibility.py',ROOT/'revk/counterface.py',
         ROOT/'revk/frontend.py',ROOT/'results/revK/revK.json']}
    (out/'compact_20mm.json').write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n')
    print({k:v for k,v in result.items() if k not in ['coil','wire','front_end','duty_by_residual']},flush=True)
    if coil['feasible_geometry']:
        print('minKm',coil['nominal_min_singular_N_sqrtW'],'worst power',
              {k:max(r['copper_power_W'] for r in d['rows']) for k,d in result['duty_by_residual'].items()},flush=True)


if __name__=='__main__':main()
