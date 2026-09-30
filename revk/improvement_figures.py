"""Reproduce review figures from the new mechanics study, without old-output edits."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
from wholepen.grounded import FiveBar,ROOT

OUT=ROOT/'results/improvement/mechanics'


def figures():
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'#fcfcfa','axes.facecolor':'#fcfcfa','savefig.facecolor':'#fcfcfa'})
    study=json.loads((OUT/'mechanics_study.json').read_text());rows=study['candidates']
    x=np.array([r['radius_mm'] for r in rows]);colors=['#15856f' if r['geometry_candidate'] else '#b95147' for r in rows]
    fig,axs=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    ax=axs[0,0];need=[r['geometry']['minimum_body_od_mm'] for r in rows]
    ax.plot(x,need,'-',c='#2c4d60');ax.scatter(x,need,c=colors,s=70,zorder=3)
    ax.axhline(24,c='#6d7477',ls='--',label='24 mm studied body')
    ax.set(xlabel='Usable mechanical radius (mm)',ylabel='Minimum body diameter (mm)',title='A. Guide and wire clearance bound')
    ax.legend(fontsize=8)
    ax=axs[0,1]
    for load,col in [(.02,'#15856f'),(.04,'#de932d'),(.08,'#b95147')]:
        power=[max(v['copper_power_W'] for v in r['duty_by_residual'][str(load)]['rows']) for r in rows]
        ax.plot(x,power,'o-',c=col,label=f'{load*1000:.0f} mN residual load')
    ax.axhline(.15,c='#444',ls='--',label='Assumed 0.15 W heat allocation')
    ax.set(yscale='log',xlabel='Usable mechanical radius (mm)',ylabel='Worst average copper loss (W)',title='B. Full-radius 4, 8 and 12 Hz motion')
    ax.legend(fontsize=8)
    ax=axs[1,0]
    ax.plot(x,[r['coil']['nominal_min_singular_N_sqrtW'] for r in rows],'o-',c='#2c4d60',label='Image-field calculation')
    ax.plot(x,[.7*r['coil']['nominal_min_singular_N_sqrtW'] for r in rows],'s--',c='#15856f',label='0.7 field sensitivity used in load screen')
    ax.set(xlabel='Usable mechanical radius (mm)',ylabel='Minimum force / √copper power (N/√W)',title='C. Force authority falls toward the edge')
    ax.legend(fontsize=8)
    ax=axs[1,1]
    ax.plot(x,[r['wire']['length_mm'] for r in rows],'o-',c='#2c4d60')
    for r in rows:
        ax.annotate(f"SF {r['wire']['worst_corner']['goodman_sf_conservative']:.2f}",
                    (r['radius_mm'],r['wire']['length_mm']),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
    ax.set(xlabel='Usable mechanical radius (mm)',ylabel='Required free wire length (mm)',title='D. Eight 0.10 mm leads; conservative fatigue corner')
    ax.set_ylim(26,55)
    fig.suptitle('Compact nib trade study — calculated design candidates, not measured performance',fontsize=14)
    fig.savefig(OUT/'mechanics_trade.png',dpi=190);fig.savefig(OUT/'mechanics_trade.svg');plt.close(fig)

    if (OUT/'compact_20mm.json').exists():
        compact=json.loads((OUT/'compact_20mm.json').read_text())
        compared=[rows[0],compact]
        fig,(a,b)=plt.subplots(1,2,figsize=(11,4.8),constrained_layout=True)
        for item,label,col in zip(compared,['24 mm body','20 mm body'],['#15856f','#be762b']):
            power=[max(r['copper_power_W'] for r in item['duty_by_residual'][str(load)]['rows']) for load in [.02,.04,.08]]
            a.plot([20,40,80],power,'o-',color=col,label=label)
            for xx,yy in zip([20,40,80],power):
                a.annotate(f'{yy:.3f}',(xx,yy),xytext=(0,6),textcoords='offset points',ha='center',fontsize=8)
        a.axhline(.15,ls='--',color='#444',label='Assumed 0.15 W copper allocation')
        a.set(yscale='log',xlabel='Assumed residual load (mN)',ylabel='Worst average copper loss (W)',
              title='A. Same 1.0587 mm radius, fresh resized field maps')
        a.legend(fontsize=8,loc='lower right')
        values=[r['coil']['nominal_min_singular_N_sqrtW'] for r in compared]
        bars=b.bar([0,1],values,color=['#15856f','#be762b'],width=.6)
        for bar,val in zip(bars,values):
            b.text(bar.get_x()+bar.get_width()/2,val+.004,f'{val:.4f}',ha='center')
        b.set(xticks=[0,1],xticklabels=['24 mm body','20 mm body'],ylim=(0,.27),
              ylabel='Minimum nominal force / √copper power (N/√W)',
              title='B. Smaller magnets reduce force authority')
        fig.suptitle('Compaction screen — component calculations, no manufactured 20 mm pen',fontsize=14)
        fig.supxlabel('20 mm: guide and wire envelope fits; 14 / 248 counter-face candidates fit. Whole assembly remains unresolved.',fontsize=9)
        fig.savefig(OUT/'compact_20mm_comparison.png',dpi=190);fig.savefig(OUT/'compact_20mm_comparison.svg');plt.close(fig)

    row=rows[1];g=row['geometry'];coil=row['coil'];wire=row['wire'];shape=coil['shape_m'];mg=coil['magnet_geometry_m']
    fig,(a,b)=plt.subplots(1,2,figsize=(12,5.5),gridspec_kw={'width_ratios':[1,1.25]},constrained_layout=True)
    a.add_patch(Circle((0,0),12,fill=False,lw=2,ec='#2c4d60'))
    a.add_patch(Circle((0,0),11,fill=False,ls='--',ec='#95a4ab'))
    for signx,signy in [(1,1),(-1,1),(-1,-1),(1,-1)]:
        w=mg['w']*1000;centre=(mg['e']+mg['w']/2)*1000
        a.add_patch(Rectangle((signx*centre-w/2,signy*centre-w/2),w,w,fc='#de8177' if signx*signy>0 else '#83a5ca',alpha=.7))
    for rr in (g['race_inner_radius_mm'],g['race_inner_radius_mm']+g['race_width_mm']):
        a.add_patch(Circle((0,0),rr,fill=False,lw=1,ec='#555'))
    for angle in np.arange(6)*np.pi/3:
        a.add_patch(Circle(g['ball_circle_radius_mm']*np.array([np.cos(angle),np.sin(angle)]),.4,fc='#444'))
    for angle in (np.arange(8)+.5)*np.pi/4:
        p=g['wire_circle_mm']*np.array([np.cos(angle),np.sin(angle)])
        a.plot(*p,'o',c='#b07717',ms=4)
    a.add_patch(Circle((0,0),1.6,fc='#cbd5dc',ec='#2c4d60'))
    a.add_patch(Circle((0,0),1.6+1.7,fill=False,ls=':',ec='#15967d'))
    a.set(xlim=(-13,13),ylim=(-13,13),aspect='equal',xlabel='x (mm)',ylabel='y (mm)',title='1.5 mm candidate: front view')
    a.text(0,-12.7,'24 mm body; 22 mm bore; 1.7 mm stop',ha='center',va='bottom',fontsize=9)
    # Dimensioned longitudinal diagram; exact solids are in the STEP file.
    zmag=23.2;zcoil=zmag+mg['t_m']*1000+mg['c0']*1000;zkeep=zcoil+(mg['t_x']+mg['t_y'])*1000+mg['c1']*1000
    zflange=zkeep+1.1;zstart=zflange+.75;zend=zstart+wire['length_mm']
    b.add_patch(Rectangle((18,-12),zend-16,24,fill=False,ec='#2c4d60',lw=2))
    for z,h,half,col,label in [(zmag,mg['t_m']*1000,9,'#b95147','Magnets'),(zcoil,1.6,8.5,'#c48c2c','Winding'),
                               (zflange,1.5,g['flange_radius_mm'],'#7095ad','Flange'),(zend,.2,10.5,'#15856f','Floating anchor')]:
        b.add_patch(Rectangle((z,-half),h,2*half,fc=col,alpha=.85))
        b.annotate(label,(z+h/2,half),xytext=(z+h/2,15+(3 if label=='Winding' else 0)),ha='center',fontsize=8,
                   arrowprops={'arrowstyle':'-','color':col})
    for sy in [-1,1]:b.plot([zstart,zend],[sy*g['wire_circle_mm']]*2,c='#b07717',lw=2)
    b.add_patch(Rectangle((9,-1.6),zflange+1.5-9,3.2,fc='#99a7b4'))
    b.annotate('',(zstart,-8),(zend,-8),arrowprops={'arrowstyle':'<->','color':'#444'})
    b.text((zstart+zend)/2,-7,'34 mm lead suspension',ha='center',fontsize=9)
    b.set(xlim=(15,zend+4),ylim=(-15,23),xlabel='Distance along pen datum (mm)',ylabel='Radial dimension (mm)',title='Longitudinal mechanism envelope')
    b.text(16,-14,'Counter-face head, electronics and flex-cable routing remain unresolved.',fontsize=8)
    fig.suptitle('Revised guide, winding and floating lead anchor — proposed geometry',fontsize=14)
    fig.savefig(OUT/'nib_layout.png',dpi=190);fig.savefig(OUT/'nib_layout.svg');plt.close(fig)

    stage=FiveBar();grid=json.loads((OUT/'grounded_stage.json').read_text())['grid']
    fig,(a,b)=plt.subplots(1,2,figsize=(12,5.3),constrained_layout=True)
    kin=stage.kinematics([0,stage.centre_y]);p=kin['point']*1000
    for base,elbow in zip(kin['bases']*1000,kin['elbows']*1000):
        a.plot([base[0],elbow[0],p[0]],[base[1],elbow[1],p[1]],'o-',lw=5,c='#15856f',mec='#253d49')
        a.add_patch(Circle(base,18,fill=False,ec='#c48c2c',lw=2))
    a.add_patch(Rectangle((-30,70),60,40,fill=False,ls='--',ec='#276983'))
    a.add_patch(Circle(p,12,fill=False,ec='#b95147',lw=2))
    a.text(0,117,'60 × 40 mm calculated workspace',ha='center')
    a.text(0,-28,'Fixed motors; 6:1 transmission; desk reaction',ha='center',fontsize=9)
    a.set(xlim=(-95,95),ylim=(-35,125),aspect='equal',xlabel='x (mm)',ylabel='y (mm)',title='A. Five-bar layout, 60 / 90 mm links')
    sc=b.scatter([r['x_mm'] for r in grid],[r['y_mm'] for r in grid],c=[r['force_radius_N'] for r in grid],cmap='viridis',s=35)
    b.set(aspect='equal',xlabel='x (mm)',ylabel='y (mm)',title='B. Nominal continuous force disk')
    fig.colorbar(sc,ax=b,label='Force guaranteed in every direction by nominal torque model (N)',shrink=.8)
    fig.suptitle('Grounded accepted-writing demonstrator — authority outside the pen',fontsize=14)
    fig.savefig(OUT/'grounded_layout.png',dpi=190);fig.savefig(OUT/'grounded_layout.svg');plt.close(fig)

    if (OUT/'grounded_replay.json').exists():
        data=json.loads((OUT/'grounded_replay.json').read_text());fig,axs=plt.subplots(1,3,figsize=(14,4.6),constrained_layout=True)
        for name,label,color in [('grounded_0N_m_feedback','Feedback only','#bc6960'),('grounded_0N_m_ff','Feedforward + feedback','#15856f'),('grounded_200N_m_ff','200 N/m resisting grip','#d9992a')]:
            trace=np.load(OUT/(name+'.npz'));ink=trace['ink'];a=axs[0]
            if name.endswith('_feedback'):a.plot(*trace['reference_xy'].T*1000,'--',c='#444',label='Requested accepted stroke')
            shown=trace['actual_xy'].copy();shown[~ink]=np.nan
            a.plot(*shown.T*1000,c=color,label=label)
            axs[1].plot(trace['t'],trace['error_m']*1000,c=color,label=label)
            axs[2].plot(trace['t'],np.linalg.norm(trace['coarse_force_N'],axis=1),c=color,label=label)
        axs[0].set(xlabel='x (mm)',ylabel='y (mm)',aspect='equal',title='A. Simulated actual contact strokes')
        axs[0].legend(fontsize=7,loc='best')
        axs[1].axhline(.2,ls=':',c='#444');axs[1].set(xlabel='Time (s)',ylabel='Error from accepted trajectory (mm)',title='B. Error and refusal threshold')
        axs[2].axhline(.4,ls=':',c='#444');axs[2].set(xlabel='Time (s)',ylabel='Coarse actuator force (N)',title='C. Motor authority remains bounded')
        fig.suptitle('One coupled reference replay — assumptions and refusal count alongside accuracy',fontsize=14)
        fig.savefig(OUT/'grounded_tracking.png',dpi=190);fig.savefig(OUT/'grounded_tracking.svg');plt.close(fig)
    if (OUT/'grounded_batch.json').exists():
        batch=json.loads((OUT/'grounded_batch.json').read_text())
        if 'summary' not in batch:return
        summary=batch['summary'];fig,axs=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
        labels=['Feedback\nonly\n0 N/m','Feedforward\n+ feedback\n0 N/m','Feedforward\n+ feedback\n200 N/m','Feedforward\n+ feedback\n500 N/m']
        cc=['#b66a5f','#15856f','#d19a31','#8a607e']
        bars=axs[0,0].bar(range(4),[r['engineering_complete'] for r in summary],color=cc)
        for bar,r in zip(bars,summary):
            axs[0,0].text(bar.get_x()+bar.get_width()/2,bar.get_height()+.3,f"{r['engineering_complete']}/{r['words']}",ha='center')
        axs[0,0].set(xticks=range(4),xticklabels=labels,ylim=(0,22),ylabel='Suffixes meeting ink / tracking criterion',title='A. Ink / tracking criterion; all writers counted')
        axs[0,1].bar(range(4),[r['median_ink_coverage']*100 for r in summary],color=cc)
        axs[0,1].set(xticks=range(4),xticklabels=labels,ylim=(0,110),ylabel='Median requested-ink time with actual contact (%)',title='B. Coverage accompanies tracking accuracy')
        for ax in axs[0]:ax.tick_params(axis='x',labelsize=9)
        for grip,colour,label in [(0,'#15856f','Unloaded stage'),(200,'#d19a31','200 N/m resisting grip')]:
            path=OUT/'grounded_words'/f'tst_UJI_W12_{grip}N_m_ff.npz'
            trace=np.load(path);actual=trace['actual_xy'].copy();actual[~trace['ink']]=np.nan
            ref=trace['reference_xy'].copy();ref[~trace['requested']]=np.nan
            ax=axs[1,0] if grip==0 else axs[1,1]
            ax.plot(*ref.T*1000,'--',color='#3c4346',label='Accepted reference')
            ax.plot(*actual.T*1000,color=colour,label='Simulated actual ink')
            row=next(r for r in batch['rows'] if r['writer']=='tst_UJI_W12' and r['grip_stiffness_N_m']==grip and r['feedforward'])
            ax.set(aspect='equal',xlabel='x on writing patch (mm)',ylabel='y (mm)',title=f'{"C" if grip==0 else "D"}. {label}; '+('completed' if row['engineering_complete'] else 'failed / refused'))
            ax.legend(fontsize=8)
        fig.suptitle('Coupled accepted-writing study: 20 template writers, 40 letters per condition',fontsize=14)
        fig.supxlabel('Actual acceleration and sampled jerk exceed the separate 2 m/s² and 300 m/s³ comparisons in all 20 unloaded traces.',fontsize=9)
        fig.savefig(OUT/'grounded_batch_summary.png',dpi=190);fig.savefig(OUT/'grounded_batch_summary.svg');plt.close(fig)
    print(OUT)


if __name__=='__main__':figures()
