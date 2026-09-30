"""Independent local pole screen for the coupled delayed-position controller.

Local linearisation only. It cannot establish nonlinear contact stability,
but it prevents choosing a bandwidth from the continuous plant alone.
"""
import json
from pathlib import Path
import numpy as np
from .grounded import FiveBar,ROOT
from revk.feasibility import page_to_nib_matrix


def pole_radius(fine_hz=25.,coarse_hz=9.,mass_scale=1.,fine_drag=0.,coarse_drag=0.,dt=.0005):
    A=np.linalg.inv(page_to_nib_matrix(50));m=.003669975;Mc=FiveBar().mass_matrix([0,.09])
    H=np.block([[Mc+m*np.eye(2),m*A],[m*A.T,m*A.T@A]])*mass_scale
    K=np.zeros((4,4));D=np.zeros((4,4))
    K[:2,:2]=Mc*(2*np.pi*coarse_hz)**2;D[:2,:2]=Mc*2*.9*2*np.pi*coarse_hz
    K[2:,2:]=m*A.T@A*(2*np.pi*fine_hz)**2;D[2:,2:]=m*A.T@A*2*.85*2*np.pi*fine_hz
    C=np.diag([coarse_drag,coarse_drag,fine_drag,fine_drag]);Ks=np.diag([0.,0.,2.,2.])
    delay=round(.002/dt);history_len=delay+1;alpha=1-np.exp(-2*np.pi*100*dt)
    dim=16+4*history_len
    def advance(s):
        x=s[:4];v=s[4:8];hist=s[8:8+4*history_len].reshape(history_len,4)
        previous=s[-8:-4];oldvel=s[-4:];measured=hist[0]
        vest=oldvel+alpha*((measured-previous)/dt-oldvel)
        estimated=measured+vest*delay*dt
        force=-K@estimated-D@vest-Ks@x-C@v
        newv=v+np.linalg.solve(H,force)*dt;newx=x+newv*dt
        return np.r_[newx,newv,np.vstack([hist[1:],newx]).ravel(),measured,vest]
    transition=np.column_stack([advance(np.eye(dim)[i]) for i in range(dim)])
    ev=np.linalg.eigvals(transition)
    return float(max(abs(ev)))


def main():
    rows=[]
    for hz in [15.,20.,25.,30.,35.,40.,45.]:
        cases=[pole_radius(hz,mass_scale=m,fine_drag=fd,coarse_drag=cd)
               for m in [.8,1.,1.2] for fd in [0.,.2,2.,8.] for cd in [0.,80.2]]
        rows.append(dict(fine_bandwidth_Hz=hz,worst_pole_radius=max(cases),stable_all_linear_corners=max(cases)<1.))
    result=dict(status='CALC local delayed-controller pole screen, not full nonlinear proof',
                cases_per_gain=24,rows=rows,parameters={'mass_scale':[.8,1.,1.2],
                    'fine_drag_Ns_m':[0.,.2,2.,8.],'coarse_drag_Ns_m':[0.,80.2],
                    'coarse_bandwidth_Hz':9.,'sensor_delay_s':.002,'velocity_filter_Hz':100.,'dt_s':.0005})
    (ROOT/'results/improvement/mechanics/grounded_servo_design.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
