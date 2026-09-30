"""Independent free-decay diagnostic for the accepted-writing friction law.

With no input, a dissipative friction force must not create kinetic energy.
For m*v' = -F*tanh(v/vs), the exact solution is
v(t) = vs*asinh(sinh(v0/vs)*exp(-F*t/(m*vs))).
This isolated analytic case diagnoses integration, not physical friction fit.
"""
from pathlib import Path
import json
import numpy as np


def study():
    mass, force, scale, v0, duration = .00344, .020, .0005, 1e-6, .020
    rows=[]
    for dt in [.0005, .0001, .00005]:
        t=np.arange(round(duration/dt)+1)*dt
        exact=scale*np.arcsinh(np.sinh(v0/scale)*np.exp(-force*t/(mass*scale)))
        v=np.empty_like(t);v[0]=v0
        for i in range(len(t)-1):
            v[i+1]=v[i]-dt*force*np.tanh(v[i]/scale)/mass
        rows.append(dict(dt_s=dt,near_zero_euler_multiplier=1-dt*force/(mass*scale),
                         peak_velocity_m_s=float(abs(v).max()),
                         peak_energy_over_initial=float(np.max(v*v)/(v0*v0)),
                         maximum_error_against_exact_m_s=float(abs(v-exact).max()),
                         exact_energy_monotone=bool(np.all(np.diff(exact**2)<=0)),
                         numerical_energy_monotone=bool(np.all(np.diff(v*v)<=1e-30))))
    return dict(evidence="Analytic numerical-integrity diagnostic; no hardware measurement",
                parameters=dict(mass_kg=mass,drag_N=force,velocity_scale_m_s=scale,
                                initial_velocity_m_s=v0,duration_s=duration),
                forward_euler_linear_stability_dt_max_s=2*mass*scale/force,
                exact_solution="v=vs*asinh(sinh(v0/vs)*exp(-F*t/(m*vs)))",rows=rows)


if __name__=='__main__':
    result=study()
    target=Path(__file__).resolve().parents[1]/'results/improvement/verification/friction_integrity.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
