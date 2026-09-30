"""Render the exact proposed fine-stage CAD solids for a review preview."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from .improved_nib import build, ROOT


def main():
    out=ROOT/'results/improvement/mechanics';data=json.loads((out/'mechanics_study.json').read_text())
    row=next(r for r in data['candidates'] if r['radius_mm']==1.5)
    assy,_,_=build(row)
    fig=plt.figure(figsize=(12,6),facecolor='#fcfcfa')
    for idx,(elev,azim,title) in enumerate([(18,-64,'Proposed solids; keep-outs hidden'),(86,-90,'Guide, winding and lead positions')]):
        ax=fig.add_subplot(1,2,idx+1,projection='3d',facecolor='#fcfcfa')
        for node in assy.children:
            if 'keepout' in node.name or 'envelope' in node.name:continue
            shape=node.obj.val() if hasattr(node.obj,'val') else node.obj
            verts,tri=shape.tessellate(.18)
            xyz=np.array([v.toTuple() for v in verts]);faces=xyz[np.array(tri)]
            color=node.color.toTuple()[:3] if node.color else (.5,.5,.5)
            coll=Poly3DCollection(faces,facecolor=color,edgecolor='none',alpha=1)
            ax.add_collection3d(coll)
        ax.set(xlim=(-12,12),ylim=(-12,12),zlim=(7,68),xlabel='x (mm)',ylabel='y (mm)',zlabel='Pen datum z (mm)',title=title)
        ax.set_box_aspect((24,24,61));ax.view_init(elev=elev,azim=azim)
        if idx==1:
            ax.set_zticks([]);ax.set_zlabel('')
    fig.suptitle('1.5 mm radial nib candidate — rendering of the parametric STEP geometry',fontsize=15)
    fig.text(.5,.02,'Proposed layout: head joints, coil supports, cable routing and complete assembly clearances remain unresolved.',ha='center',fontsize=10)
    fig.subplots_adjust(left=.02,right=.98,top=.88,bottom=.13,wspace=.10)
    fig.savefig(out/'nib_cad_preview.png',dpi=180)
    print(out/'nib_cad_preview.png')


if __name__=='__main__':main()
