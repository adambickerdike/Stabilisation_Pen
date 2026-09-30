"""Recover the lost numerical surrogate from its committed study observations.

This is reproducibility work, not refitting to make a new design pass. The
committed study stores hundreds of geometries and the old analytic copper power.
The force numerator is independent of the magnetic calibration, so those records
identify its nine log-linear coefficients. Full column rank, fit residuals and
an independent forward magnetic check must pass before the snapshot is written.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def recover():
    from . import REPO_ROOT
    from . import actuators as A, candidates as C, optimise as O
    path=REPO_ROOT/'results/bnib/bnib.json'
    report=json.loads(path.read_text())
    records=[p for group in ('pen24','slim') for p in report['optimisation']['fronts'][group]['pareto_all']
             if p['key']=='c_counterface' and p.get('family')=='translation']
    X=[];Y=[];nu=[]
    for p in records:
        d=replace(O.build(p['key'],p['grip'],p['x']),km_scale=O.KM_OBJ)
        r=C.evaluate(d,detail=False,fast=True)
        Km=r['Km_tip']; k=r['k_tip_N_m']; mass=r['m_eff_tip_g']*.001
        # Exactly undo the coherent-harmonic correction for old observations.
        F2=r['P_cont_W']*Km**2+4*k*mass*(2*math.pi*C.DUTY_A.f)**2*C.DUTY_A.q_rms**2
        histKm=math.sqrt(F2/p['P_cont_W'])/O.KM_OBJ
        raw=A.vc_axial(d.w,d.t_m,d.t_c,d.travel+.0002,cal={'kappa':1.,'nu':0.})
        X.append([float(z) for z in A._kappa_features(d.w,d.t_m,float(raw['G']),d.travel+.0002,d.t_c)])
        Y.append(math.log(histKm/float(raw['Km0'])))
        if p.get('P_peak_W'):
            kmin=r['F_need_full_travel_12Hz_N']/math.sqrt(p['P_peak_W'])/O.KM_CON
            # The low-force floor must not be used to identify the linear loss.
            if kmin/histKm>.251:
                nu.append((1-kmin/histKm)*d.w/(d.travel+.0002))
    X,Y=np.array(X),np.array(Y)
    coeff,_,rank,_=np.linalg.lstsq(X,Y,rcond=None)
    error=X@coeff-Y
    if rank!=9 or np.max(abs(error))>1e-9 or np.std(nu)>1e-9:
        raise RuntimeError('historical calibration not uniquely reconstructed')
    out={'kappa':float(np.exp(np.mean(Y))),'coef':coeff.tolist(),'nu':float(np.mean(nu)),'fitted':True,
         'recovered_from_committed_numerical_observations':True,
         'recovery':{'n_observations':len(records),'matrix_rank':int(rank),'max_log_residual':float(np.max(abs(error))),
                     'nu_n_observations':len(nu),'nu_std':float(np.std(nu)),
                     'source':'results/bnib/bnib.json','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()},
         'label':'RECOVERED NUMERICAL SURROGATE: legacy full-coil magnetostatic approximation, not hardware calibration'}
    refit_path=Path(__file__).parent/'data/vc_calibration_refit.json'
    refit=json.loads(refit_path.read_text())
    errs=[]
    for row in refit['rows']:
        s={k:v*.001 if k in ('w','s','t_m','t_c','G') else v for k,v in row.items()}
        pred=s['Km0_surrogate_raw']*A.kappa_of(out,s['w'],s['t_m'],s['G'],s['s'],s['t_c'])
        errs.append(float(pred/s['Km0_magpylib']-1))
    out['n_fit']=len(records);out['n_holdout']=len(errs)
    out['rel_rms_fit']=float(np.sqrt(np.mean(error**2)))
    out['rel_rms_holdout']=float(np.sqrt(np.mean(np.array(errs)**2)))
    out['rel_max_holdout']=float(np.max(abs(np.array(errs))))
    out['independent_validation']={'source':str(refit_path.relative_to(REPO_ROOT)),
                                  'note':'50 newly executed cuboid/image force maps not used for coefficient recovery',
                                  'sha256':hashlib.sha256(refit_path.read_bytes()).hexdigest()}
    if out['rel_max_holdout']>.03: raise RuntimeError('independent field validation failed')
    A.CAL_SNAPSHOT.write_text(json.dumps(out,indent=2)+'\n')
    A.CAL_PATH.parent.mkdir(parents=True,exist_ok=True)
    A.CAL_PATH.write_text(json.dumps(out,indent=2)+'\n')
    return out


if __name__=='__main__':
    print(json.dumps(recover(),indent=2))
