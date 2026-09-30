"""Grounded five-bar coarse stage: kinematics, force authority and dynamics.

This is a *proposed laboratory demonstrator*, not a compact pen claim. It gives
accepted writing a force path to the desk. SI units throughout. Fixed-base
motors and output bearings are distinct: motor shafts must not carry link loads.
The motor data are manufacturer data; transmission, links, payload, encoder,
friction and comfort caps are explicitly unmeasured design assumptions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MOTOR_URL = "https://www.faulhaber.com/fileadmin/Import/Media/EN_2224_SR_DFF.pdf"


@dataclass(frozen=True)
class FiveBar:
    base: float = .050
    proximal: float = .060
    distal: float = .090
    centre_y: float = .090
    workspace_half_x: float = .030
    workspace_half_y: float = .020
    payload_mass: float = .080  # pen, moving bracket, load cell; excludes links
    proximal_mass: float = .006
    distal_mass: float = .008
    ratio: float = 6.
    transmission_efficiency: float = .8
    # Faulhaber 2224 U 012 SR, 2026-07-28 sheet, 22C. Rated output torque is
    # deliberately kept below kM*IN; stall torque is never a continuous rating.
    torque_constant: float = .0146
    resistance: float = 8.77
    inductance: float = 203e-6
    rotor_inertia: float = 2.7e-7
    motor_friction: float = .0002
    rated_torque: float = .00621
    rated_current: float = .485
    supply: float = 12.
    winding_rise: float = 45.
    force_cap: float = .4  # ASSUMED user interaction cap, not a clinical limit
    residual_friction: float = .08  # total unmeasured external/load allowance
    output_encoder_counts: int = 65536  # 16-bit assumed encoder ON output

    def validate(self):
        positive = (self.base, self.proximal, self.distal, self.payload_mass,
                    self.ratio, self.torque_constant, self.resistance,
                    self.rated_torque, self.rated_current, self.supply)
        if any(v <= 0 or not np.isfinite(v) for v in positive):
            raise ValueError("positive finite geometry, inertia and motor parameters required")
        if not 0 < self.transmission_efficiency <= 1:
            raise ValueError("transmission efficiency must be in (0,1]")

    def kinematics(self, xy):
        """Elbows-out assembly mode and dp/dtheta from differentiated closure.

        Singular and unreachable points fail explicitly; no clipped acos or
        pseudoinverse can silently invent reachable motion.
        """
        self.validate()
        p = np.asarray(xy, dtype=float)
        if p.shape != (2,) or not np.isfinite(p).all():
            raise ValueError("one finite planar point required")
        bases = np.array([[-self.base/2, 0], [self.base/2, 0]])
        r = p - bases
        d = np.linalg.norm(r, axis=1)
        c = (d*d + self.proximal**2-self.distal**2)/(2*d*self.proximal)
        if np.any(np.abs(c) >= 1):
            raise ValueError("unreachable or serial-singular five-bar point")
        theta = np.arctan2(r[:, 1], r[:, 0]) + np.array([1., -1.])*np.arccos(c)
        tangents = np.column_stack([-np.sin(theta), np.cos(theta)])
        elbows = bases + self.proximal*np.column_stack([np.cos(theta), np.sin(theta)])
        links = p - elbows
        A = links
        B = np.diag(np.sum(links*self.proximal*tangents, axis=1))
        if abs(np.linalg.det(A)) < 1e-7 or abs(np.linalg.det(B)) < 1e-9:
            raise ValueError("parallel or serial singularity")
        J = np.linalg.solve(A, B)
        return dict(point=p, bases=bases, angles=theta, elbows=elbows,
                    distal_vectors=links, J=J, inverse_J=np.linalg.inv(J),
                    condition=float(np.linalg.cond(J)))

    def in_workspace(self, xy):
        p = np.asarray(xy)
        return bool(abs(p[0]) <= self.workspace_half_x and
                    abs(p[1]-self.centre_y) <= self.workspace_half_y)

    def mass_matrix(self, xy, include_rotors=True):
        """Cartesian kinetic-energy matrix from link COM and angular motion.

        Uniform slender links are a model assumption. Rotors reflect through
        the squared transmission ratio; they cannot be removed from the mass
        budget just because the motors are stationary.
        """
        k = self.kinematics(xy)
        inv, theta = k['inverse_J'], k['angles']
        M = self.payload_mass*np.eye(2)
        for i in range(2):
            t = np.array([-np.sin(theta[i]), np.cos(theta[i])])
            Je = np.outer(self.proximal*t, inv[i])
            Jc = Je/2
            M += self.proximal_mass*(Jc.T@Jc)
            M += self.proximal_mass*self.proximal**2/12*np.outer(inv[i], inv[i])
            Jd = (Je+np.eye(2))/2
            u = k['distal_vectors'][i]
            angle_row = np.array([-u[1], u[0]])@(np.eye(2)-Je)/self.distal**2
            M += self.distal_mass*(Jd.T@Jd)
            M += self.distal_mass*self.distal**2/12*np.outer(angle_row, angle_row)
        if include_rotors:
            M += self.rotor_inertia*self.ratio**2*(inv.T@inv)
        return M

    def coriolis(self, xy, velocity, include_rotors=True):
        """Christoffel force from central derivatives of the energy matrix."""
        p, v = np.asarray(xy, float), np.asarray(velocity, float)
        h = 1e-6
        D = np.array([(self.mass_matrix(p+np.eye(2)[i]*h, include_rotors)-
                       self.mass_matrix(p-np.eye(2)[i]*h, include_rotors))/(2*h)
                      for i in range(2)])  # D[k,i,j] = dM_ij/dp_k
        return np.einsum('kij,j,k->i', D, v, v)-.5*np.einsum('ijk,j,k->i', D, v, v)

    def motor_requirements(self, xy, velocity, acceleration, external_force):
        """Inverse dynamics, resistive drop and reciprocal back-EMF.

        Rotor acceleration is before the transmission. Winding rise is an
        assumed design condition. Current-slew voltage is reported separately
        by trajectory_postcheck; this function does not hide L di/dt.
        """
        p, v, a, f = map(lambda x:np.asarray(x, float), (xy, velocity, acceleration, external_force))
        kin = self.kinematics(p)
        qv = kin['inverse_J']@v
        h = 1e-5
        inv_dot = (self.kinematics(p+h*v)['inverse_J']-
                   self.kinematics(p-h*v)['inverse_J'])/(2*h)
        qa = kin['inverse_J']@a + inv_dot@v
        load = self.mass_matrix(p, False)@a+self.coriolis(p, v, False)+f
        output_tau = kin['J'].T@load
        drive_tau = output_tau/(self.ratio*self.transmission_efficiency)
        drive_tau += self.rotor_inertia*self.ratio*qa
        # At rest, report the worst direction of breakaway friction.
        direction = np.where(abs(qv)>1e-8, np.sign(qv), np.sign(drive_tau))
        drive_tau += self.motor_friction*direction
        current = drive_tau/self.torque_constant
        emf = self.torque_constant*self.ratio*qv
        resistance = self.resistance*(1+.00393*self.winding_rise)
        voltage = current*resistance+emf
        return dict(current_A=current, voltage_without_Ldi_dt_V=voltage,
                    output_torque_Nm=output_tau, motor_torque_Nm=drive_tau,
                    joint_velocity_rad_s=qv, joint_acceleration_rad_s2=qa,
                    current_pass=bool(np.max(abs(current))<=self.rated_current),
                    voltage_pass=bool(np.max(abs(voltage))<=self.supply),
                    copper_power_W=float(current@current*resistance))

    def static_force_radius(self, xy):
        """Largest force disk inside the two output-torque constraints."""
        J = self.kinematics(xy)['J']
        tau = self.rated_torque*self.ratio*self.transmission_efficiency
        return float(np.min(tau/np.linalg.norm(J, axis=0)))

    def allocate_force(self, xy, requested, velocity=(0.,0.)):
        """Common scaling preserves force direction and bounds motor torque.

        This allocator is for the plant simulation, with rotor inertia in the
        plant mass matrix. It uses continuous rated torque; no stall boost.
        The user force cap bounds actuator force, not unknown external impacts.
        """
        f, v = np.asarray(requested, float), np.asarray(velocity, float)
        J = self.kinematics(xy)['J']
        n = np.linalg.norm(f)
        scale = min(1., self.force_cap/max(n, 1e-15))
        tau = J.T@f
        tau_max = self.rated_torque*self.ratio*self.transmission_efficiency
        scale = min(scale, tau_max/max(np.max(abs(tau)), 1e-15))
        qv = np.linalg.solve(J, v)
        slope = tau/(self.ratio*self.transmission_efficiency*self.torque_constant)
        offset = self.motor_friction/self.torque_constant*np.where(abs(qv)>1e-8,np.sign(qv),np.sign(tau))
        R = self.resistance*(1+.00393*self.winding_rise)
        emf = self.torque_constant*self.ratio*qv
        lower,upper=0.,scale
        # Exact intersection of current and voltage intervals along alpha*f.
        # The friction offset is present in BOTH the check and returned voltage.
        for slopes,offsets,bound in [(slope,offset,self.rated_current),(R*slope,R*offset+emf,self.supply)]:
            for si,oi in zip(slopes,offsets):
                if abs(si)<1e-15:
                    if abs(oi)>bound:upper=-1.;break
                else:
                    lo,hi=sorted(((-bound-oi)/si,(bound-oi)/si))
                    lower=max(lower,lo);upper=min(upper,hi)
        if upper<lower or upper<0:
            return dict(feasible=False,reason='no force-preserving current/voltage solution; back-EMF or friction exceeds rail',
                        force_N=np.zeros(2),authority=0.,motor_current_A=np.zeros(2),voltage_V=emf,output_torque_Nm=np.zeros(2))
        scale=upper;actual=scale*f;imotor=scale*slope+offset
        voltage=R*imotor+emf
        return dict(feasible=True,force_N=actual, authority=float(scale), motor_current_A=imotor,
                    voltage_V=voltage, output_torque_Nm=J.T@actual)


def trajectory_postcheck(path, stage=FiveBar(), out=None):
    """Read the writing agent's exact derivative export without differentiating
    quantized position samples. Current derivative is explicitly sampled.
    """
    data=np.load(path)
    p=data['coarse_offset_page_m']+np.array([0.,stage.centre_y])
    v=data['coarse_velocity_m_s']; a=data['coarse_acceleration_m_s2']
    t=data['t']
    rows=[]
    for pi,vi,ai in zip(p,v,a):
        speed=np.linalg.norm(vi)
        f=stage.residual_friction*(vi/speed if speed>1e-9 else np.array([1.,0.]))
        rows.append(stage.motor_requirements(pi,vi,ai,f))
    current=np.array([r['current_A'] for r in rows]); voltage=np.array([r['voltage_without_Ldi_dt_V'] for r in rows])
    voltage+=stage.inductance*np.gradient(current,t,axis=0)
    result={
        'status':'CALC inverse dynamics, not measured tracking or clinical benefit',
        'input':str(path),'samples':len(t),'stage':asdict(stage),'motor_source':MOTOR_URL,
        'workspace_pass':all(stage.in_workspace(pi) for pi in p),
        'current_peak_A':float(np.max(abs(current))),
        'current_rms_A':np.sqrt(np.mean(current*current,axis=0)).tolist(),
        'voltage_peak_including_sampled_Ldi_dt_V':float(np.max(abs(voltage))),
        'copper_average_W':float(np.mean([r['copper_power_W'] for r in rows])),
        'min_continuous_force_disk_N':min(stage.static_force_radius(pi) for pi in p),
        'effective_mass_eigenvalue_range_kg':[float(min(np.linalg.eigvalsh(stage.mass_matrix(pi)).min() for pi in p)),
                                              float(max(np.linalg.eigvalsh(stage.mass_matrix(pi)).max() for pi in p))],
        'force_assumption':'0.08N opposing motion; no person grip force in this inverse-dynamics check',
        'limitations':['transmission efficiency and friction unmeasured','rigid links and bearings',
                       'no backlash/flexibility in model','manufacturer rated torque at22C; mounting required',
                       '16-bit output encoder assumption, not measured positioning accuracy'],
    }
    result['electrical_pass']=bool(result['current_peak_A']<=stage.rated_current and np.max(abs(voltage))<=stage.supply)
    if out: Path(out).write_text(json.dumps(result,indent=2)+'\n')
    return result


def study(stage=FiveBar()):
    rows=[]
    for x in np.linspace(-stage.workspace_half_x,stage.workspace_half_x,25):
        for y in np.linspace(stage.centre_y-stage.workspace_half_y,stage.centre_y+stage.workspace_half_y,17):
            p=np.array([x,y]); k=stage.kinematics(p)
            rows.append(dict(x_mm=x*1000,y_mm=y*1000,condition=k['condition'],
                force_radius_N=stage.static_force_radius(p),
                mass_eigenvalues_kg=np.linalg.eigvalsh(stage.mass_matrix(p)).tolist(),
                encoder_one_count_max_um=float(np.linalg.svd(k['J'],compute_uv=False)[0]*2*np.pi/stage.output_encoder_counts*1e6)))
    return dict(status='PROPOSED mechanism, calculated authority only',motor_source=MOTOR_URL,inputs=asdict(stage),
                grid=rows,minimum_force_radius_N=min(r['force_radius_N'] for r in rows),
                worst_condition=max(r['condition'] for r in rows),
                mass_range_kg=[min(r['mass_eigenvalues_kg'][0] for r in rows),max(r['mass_eigenvalues_kg'][1] for r in rows)],
                maximum_encoder_count_um=max(r['encoder_one_count_max_um'] for r in rows),
                bore_compatibility={'original_inner_pen_od_mm':12,'new_fine_stage_od_mm':24,
                    'original_collar_od_mm':21.7,'estimated_collar_for_same_clearance_mm':33.7,
                    'status':'necessary envelope bound; original collar actuator scaling not validated'},
                reaction_mass_dc_limit='F=m*d2x/dt2; bounded internal travel cannot provide sustained static force')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trajectory',type=Path)
    ap.add_argument('--out',type=Path,default=ROOT/'results/improvement/mechanics')
    args=ap.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    result=study();(args.out/'grounded_stage.json').write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k!='grid'})
    if args.trajectory: print(trajectory_postcheck(args.trajectory,out=args.out/'grounded_trajectory.json'))


if __name__=='__main__':main()
