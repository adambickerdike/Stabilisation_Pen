"""Parametric five-bar demonstrator layout; not production CAD or an order BOM.

Output bearings carry linkage loads. Motors drive them through proposed6:1
capstan/belt transmissions; belt tensioners, preload, encoder mounts and the
pen's axial lift remain unresolved. Link endpoints match wholepen.grounded.
"""
from pathlib import Path
import json
import math
import numpy as np
import cadquery as cq
from wholepen.grounded import FiveBar, ROOT


def bar(a,b,z,width=7.,thickness=3.):
    a,b=np.asarray(a),np.asarray(b);d=b-a;L=float(np.linalg.norm(d))
    angle=math.degrees(math.atan2(d[1],d[0]))
    obj=cq.Workplane('XY').slot2D(L+width,width).extrude(thickness)
    for end in (-L/2,L/2):
        obj=obj.cut(cq.Workplane('XY').center(end,0).circle(1.5).extrude(thickness))
    return obj.rotate((0,0,0),(0,0,1),angle).translate(((a[0]+b[0])/2,(a[1]+b[1])/2,z))


def build(out):
    stage=FiveBar(); kin=stage.kinematics([0,stage.centre_y])
    assy=cq.Assembly(name='Grounded_accepted_writing_demonstrator')
    parts=[]
    def add(obj,name,color,role):
        assy.add(obj,name=name,color=cq.Color(*color));parts.append(dict(name=name,role=role,volume_mm3=obj.val().Volume()))
    add(cq.Workplane('XY').box(170,165,5,centered=(True,False,False)).translate((0,-35,-5)),
        'desk_reaction_base',(.72,.76,.8),'grounded base, bolted or clamped to desk')
    for i in range(2):
        b=kin['bases'][i]*1000;e=kin['elbows'][i]*1000;p=kin['point']*1000
        sign=-1 if i==0 else 1;motor=b+np.array([sign*29,0])
        add(cq.Workplane('XY').circle(11).extrude(24.2).translate((motor[0],motor[1],0)),
            f'motor_{i}_2224_envelope',(.32,.35,.40),'MFR envelope22×24.2mm; mass46g')
        add(cq.Workplane('XY').circle(8).circle(1.5).extrude(18).translate((b[0],b[1],0)),
            f'output_bearing_support_{i}',(.6,.64,.69),'bearing specification and preload unresolved')
        add(cq.Workplane('XY').circle(18).circle(1.5).extrude(3).translate((b[0],b[1],24.2)),
            f'output_capstan_{i}',(.82,.60,.2),'proposed outputradius18mm')
        add(cq.Workplane('XY').circle(3).circle(1).extrude(3).translate((motor[0],motor[1],24.2)),
            f'motor_capstan_{i}',(.82,.60,.2),'proposed inputradius3mm; ratio6:1; routing notresolved')
        add(bar(b,e,28+i*4),f'proximal_link_{i}',(.20,.52,.68),'60mm pin spacing, massmodel6g')
        add(bar(e,p,36+i*4),f'distal_link_{i}',(.24,.68,.55),'90mm pin spacing, massmodel8g')
        for name,pos in [('base',b),('elbow',e)]:
            add(cq.Workplane('XY').circle(1.5).extrude(25).translate((pos[0],pos[1],18)),
                f'{name}_shaft_{i}',(.35,.36,.38),'shaft and bearing load path concept')
    p=kin['point']*1000
    add(cq.Workplane('XY').circle(14).circle(12.3).extrude(6).translate((p[0],p[1],42)),
        '24mm_pen_holder_keepout',(.65,.26,.25),'holder forfine-stagepen; gimbal/loadcellgeometryunresolved')
    add(cq.Workplane('XY').rect(60,40).extrude(.1).translate((p[0],p[1],.1)),
        'calculated_workspace_keepout',(.15,.65,.76,.15),'60×40mm linkage endpoint workspace; pen-tipfixedoffsetnotshown')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    assy.export(str(out/'grounded_fivebar.step'))
    data=dict(status='PROPOSED layout, no interference certification or manufactured hardware',parts=parts,
              drive='two2224 U012SR;6:1 capstan/belt concept,80% efficiency ASSUMPTION',
              unresolved=['belt routing and tensioner','output encoders and bearing preload','pen gimbal and axial lift',
                          'link flexibility, backlash, fatigue and guards','supply, drivers and emergency force release'],
              board_mm=[170,165,5],endpoint_link_spacing_mm=[60,90,50],
              note='Existing24mm pen retained; this deliberately exports reaction and travel to a board, not inside a slim collar')
    (out/'grounded_cad_summary.json').write_text(json.dumps(data,indent=2)+'\n')
    print(out/'grounded_fivebar.step')


if __name__=='__main__':build(ROOT/'results/improvement/mechanics')
