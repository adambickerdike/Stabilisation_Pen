"""Parametric, reviewable extended-reach nib + floating-anchor coupon.

Run after `python -m revk.improve`. Not a production drawing or a fully validated
assembly: magnets, winding packs, guide races, wires and anchor are solid CAD;
the counter-face head is a swept-envelope keep-out, explicitly not a resolved
mechanism. Clearances recorded are analytical swept-envelope checks, not an
invented global collision-free certificate.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parents[2]


def ring(ro, ri, z, h):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((0, 0, z))


def build(candidate):
    geom, coil, wire = candidate['geometry'], candidate['coil'], candidate['wire']
    if not geom['guide_wire_fit']:
        raise ValueError('this candidate needs a different guide/body; refuse a misleading CAD assembly')
    shape = {k:v*1000 for k,v in coil['shape_m'].items()}
    mg = coil['magnet_geometry_m']
    total_h = (mg['t_x']+mg['t_y'])*1000
    mag_z = 23.2
    coil_z = mag_z + mg['t_m']*1000 + mg['c0']*1000
    keeper_z = coil_z + total_h + mg['c1']*1000
    flange_z = keeper_z + .3 + .8
    wire_z = flange_z + .75
    L=wire['length_mm']; end=wire_z+L
    n=wire['n_wires']; r=geom['wire_circle_mm']
    assy=cq.Assembly(name='Proposed_extended_reach_nib')
    masses=[]
    def add(obj,name,color,density=None):
        assy.add(obj,name=name,color=cq.Color(*color))
        if density:
            masses.append({'part':name,'solid_mass_g':obj.val().Volume()*density*.001})
    add(ring(geom['bore_radius_mm'],geom['bore_radius_mm']-.2,18,end-16),'bore_keepout',(.65,.70,.75,.12))
    centre=(mg['e']+mg['w']/2)*1000
    hole=1.6+geom['stop_mm']+.3
    rout=math.sqrt(2)*(mg['e']+mg['w'])*1000+.2
    add(ring(rout,hole,mag_z-.5,.5),'back_iron',(.3,.34,.38),7.85)
    add(ring(rout,hole,keeper_z,.3),'keeper_with_front_race_surface',(.3,.34,.38),7.85)
    for i,(sx,sy) in enumerate([(1,1),(-1,1),(-1,-1),(1,-1)]):
        w=mg['w']*1000; h=mg['t_m']*1000
        obj=cq.Workplane('XY').box(w,w,h,centered=(True,True,False)).translate((sx*centre,sy*centre,mag_z))
        add(obj,f'N52_pole_{i+1}',(.70,.25,.25) if sx*sy>0 else (.2,.35,.7),7.5)
    order=coil['order']; gap=.05; active=(total_h-(len(order)-1)*gap)/len(order)
    for layer,axis in enumerate(order):
        z=coil_z+layer*(active+gap)
        for sign in (-1,1):
            xi,yi,b,yc=shape['x_in'],shape['y_in'],shape['bundle'],shape['row_centre']
            obj=(cq.Workplane('XY').rect(2*(xi+b),2*(yi+b)).rect(2*xi,2*yi).extrude(active)
                 .translate((0,sign*yc,z)))
            if axis=='y': obj=obj.rotate((0,0,0),(0,0,1),90)
            add(obj,f'winding_pack_{layer}_{sign}',(.83,.49,.16))
    # Cylinder clearance is conservative for every radial displacement direction.
    add(ring(1.6,1.25,9,flange_z+1.5-9),'carrier_tube',(.6,.62,.66),4.43)
    add(ring(geom['flange_radius_mm'],1.3,flange_z,1.5),'moving_flange',(.58,.62,.68),4.43)
    bc=geom['ball_circle_radius_mm']; rw=geom['race_width_mm']
    for side,z in [('front',keeper_z),('rear',flange_z+1.5+.8)]:
        if side=='rear':
            add(ring(bc+rw/2,bc-rw/2,z,.3),f'{side}_race',(.48,.50,.54),7.8)
        bz=keeper_z+.3+.4 if side=='front' else flange_z+1.5+.4
        for i in range(6):
            a=2*math.pi*i/6
            obj=cq.Workplane('XY').sphere(.4).translate((bc*math.cos(a),bc*math.sin(a),bz))
            add(obj,f'{side}_Si3N4_ball_{i+1}',(.12,.14,.16),3.2)
    for i in range(n):
        a=2*math.pi*(i+.5)/n
        obj=cq.Workplane('XY').circle(wire['diameter_mm']/2).extrude(L).translate((r*math.cos(a),r*math.sin(a),wire_z))
        add(obj,f'C17200_lead_suspension_{i+1}',(.75,.53,.25),8.25)
    # Four radial fixed-guided leaf beams, not an unspecified 'soft diaphragm'.
    ri=1.175+geom['stop_mm']+.3
    hub_outer=max(r+.35,ri+.5)
    beam_length=6.0; beam_width=.5; beam_t=.035
    outer_start=hub_outer+beam_length
    if outer_start+.3>geom['bore_radius_mm']:
        raise ValueError('diaphragm coupon does not fit bore; increase compliance length by another topology')
    diaphragm=ring(hub_outer,ri,0,beam_t).union(ring(outer_start+.3,outer_start,0,beam_t))
    for a in (0,90,180,270):
        leaf=cq.Workplane('XY').box(beam_length+.04,beam_width,beam_t,centered=(True,True,False)).translate((hub_outer+beam_length/2,0,0)).rotate((0,0,0),(0,0,1),a)
        diaphragm=diaphragm.union(leaf)
    add(diaphragm.translate((0,0,end)),'301_steel_floating_anchor',(.6,.67,.72),8.0)
    # Refill holder extension permits the longer wires without silently placing
    # the anchor in the counter-face's original swept volume.
    extension=wire['holder_and_body_extension_mm']
    add(cq.Workplane('XY').circle(1.175).extrude(64+extension).translate((0,0,3)),
        'refill_and_extension_envelope',(.16,.19,.24))
    head=candidate['head']
    if head:
        z0,z1=head['swept_z_mm']
        add(cq.Workplane('XY').circle(head['swept_r_max_mm']).extrude(z1-z0).translate((0,0,z0+extension)),
            'counterface_swept_keepout_UNRESOLVED',(.12,.68,.68,.15))
        head_gap=z0+extension-(end+beam_t)
        if head_gap<.3:
            raise ValueError('head swept envelope does not clear extended wire anchor axially')
    else:
        head_gap=None
    E=193e9
    k=4*E*(beam_width*.001)*(beam_t*.001)**3/(beam_length*.001)**3
    qa={
        'evidence_status':'PROPOSED CAD and calculations, not manufactured or collision-certified',
        'radius_mm':candidate['radius_mm'],'body_od_mm':geom['body_od_mm'],
        'wire_count':n,'wire_length_mm':L,'wire_circle_radius_mm':r,
        'head_swept_axial_gap_from_anchor_mm':head_gap,
        'body_length_estimate_mm':145.1+extension,'holder_extension_mm':extension,
        'diaphragm':{'material':'301 steel, E193GPa ASSUMPTION','beam_count':4,'beam_length_mm':beam_length,
                     'beam_width_mm':beam_width,'thickness_mm':beam_t,'calculated_axial_stiffness_N_m':k,
                     'target_total_including_flex_cable_N_m':100.,
                     'nominal_flex_cable_stiffness_allowance_N_m':100.-k,
                     'target_tolerance_N_m':[80.,120.],
                     'requires_measured_clamp_stiffness':True},
        'swept_clearance_checks':geom,
        'solid_mass_partial_g':sum(x['solid_mass_g'] for x in masses),'partial_mass_breakdown':masses,
        'unresolved':['full head joints/float','diaphragm flex cable and solder pads','3D package with electronics',
                      'Hall sensor relocation and field calibration','guide race/support compliance',
                      'coil former, actual winding turns and insulation processing','drop stops and dust protection'],
        'components':len(assy.children),
    }
    return assy,diaphragm,qa


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--radius',type=float,default=1.5)
    ap.add_argument('--out',type=Path,default=ROOT/'results/improvement/mechanics')
    args=ap.parse_args(argv)
    study=json.loads((args.out/'mechanics_study.json').read_text())
    candidate=min(study['candidates'],key=lambda x:abs(x['radius_mm']-args.radius))
    if abs(candidate['radius_mm']-args.radius)>.01: raise ValueError('requested study candidate absent')
    assy,coupon,qa=build(candidate)
    assy.export(str(args.out/'extended_reach_nib.step'))
    cq.exporters.export(coupon,str(args.out/'floating_anchor_coupon.step'))
    (args.out/'cad_summary.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))


if __name__=='__main__': main()
