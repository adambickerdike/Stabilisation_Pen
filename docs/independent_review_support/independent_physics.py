"""Independent pen feasibility calculations; Python 3 standard library only.

CALCULATION, not hardware validation. SI units internally; explicit output units.
Run: python3 independent_physics.py --out results
Inputs from repository b1694a3 or explicitly illustrative assumptions below.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import unittest

BASE_COMMIT = "b1694a3a35fe134026c93786dbae673c3fdbfd85"

def static_load(theta_deg, axial_force=0.15, tip_arm=0.07648,
                actuator_arm=0.0115, motor_constant=0.656, resistance=2.47):
    # Frictionless, maintained contact, refill slides along its axis.
    transverse = axial_force / math.tan(math.radians(theta_deg))
    torque = transverse * tip_arm
    force = torque / actuator_arm
    power = (force / motor_constant) ** 2
    return dict(tilt_deg=theta_deg, transverse_N=transverse, torque_Nm=torque,
                actuator_force_N=force, copper_W=power,
                current_A=math.sqrt(power/resistance))

def reaction_force(f_hz, mass_kg=0.030, half_stroke_m=0.004):
    # Fixed-base sinusoidal stroke envelope, excludes actuator/thermal caps.
    return mass_kg * (2*math.pi*f_hz)**2 * half_stroke_m

def residual(f_hz, latency_s):
    # Exact unit-gain, otherwise-perfect cancellation with pure time delay.
    return 2*abs(math.sin(math.pi*f_hz*latency_s))

def heat_time(power_W, resistance_K_W=100, capacity_J_K=0.5,
              ambient_C=25, limit_C=120):
    delta = limit_C-ambient_C
    if power_W*resistance_K_W <= delta:
        return None
    return -resistance_K_W*capacity_J_K*math.log1p(-delta/(power_W*resistance_K_W))

def generate():
    a=static_load(50)
    angular_speed=30000*2*math.pi/60
    mass, radius=0.020,0.006
    inertia=0.5*mass*radius**2
    h=inertia*angular_speed
    rotor=dict(mass_kg=mass,radius_m=radius,speed_rpm=30000,inertia_kg_m2=inertia,
               momentum_Nm_s=h,energy_J=0.5*inertia*angular_speed**2,
               torque_at_5Hz_20deg_Nm=h*(2*math.pi*5)*math.radians(20),
               diameter_for_0_005_Nm_s_mm=2000*math.sqrt(2*0.005/(mass*angular_speed)),
               energy_for_0_005_Nm_s_J=0.5*0.005*angular_speed)
    packing=[]
    for outer_mm in (14,16,18,20,22,24):
        inner=outer_mm-2
        slug_d=inner-8
        volume=30/19.3*1000  # 30 g, illustrative solid tungsten density g/cm3
        packing.append(dict(outer_diameter_mm=outer_mm,wall_mm=1,
                            radial_half_stroke_mm=4,slug_diameter_mm=slug_d,
                            slug_length_mm=volume/(math.pi*slug_d**2/4)))
    result=dict(
      evidence_class="CALCULATION; no physical or clinical validation",
      source_commit=BASE_COMMIT,
      assumptions=dict(axial_force_N=0.15,tip_arm_m=0.07648,actuator_arm_m=0.0115,
                       motor_constant_N_sqrtW=0.656,resistance_ohm=2.47,
                       reaction_mass_kg=0.030,radial_half_stroke_m=0.004,
                       thermal_resistance_K_W=100,thermal_capacity_J_K=0.5,
                       ambient_C=25,coil_limit_C=120,
                       usable_energy_Wh=2.22),
      static=[static_load(t) for t in (35,50,75)],
      static_curve=[static_load(t) for t in range(35,76)],
      balanced_static_50deg_W=a['copper_W']*0.1**2,
      half_axial_force_50deg_W=static_load(50,axial_force=0.075)['copper_W'],
      longer_arm_34mm_50deg_W=static_load(50,actuator_arm=0.034)['copper_W'],
      reaction=[dict(frequency_Hz=f,force_N=reaction_force(f),
                     stroke_for_0_5N_mm=1000*0.5/(0.03*(2*math.pi*f)**2),
                     tail_torque_70mm_Nm=0.07*reaction_force(f)) for f in (1,3,5,8,10,12)],
      reaction_curve=[dict(frequency_Hz=f/10,force_N=reaction_force(f/10)) for f in range(1,121)],
      delay=[dict(frequency_Hz=f,latency_ms=t,residual_amplitude_ratio=residual(f,t/1000))
             for f in (4,6,8,10,12) for t in (2,5,10)],
      delay_70pct_reduction_10Hz_ms=1000*math.asin(0.3/2)/(math.pi*10),
      thermal=[dict(power_W=p,time_to_120C_s=heat_time(p),
                    extrapolated_steady_coil_C=25+100*p) for p in (a['copper_W'],2.68)],
      battery=[dict(total_power_W=p,ideal_runtime_h=2.22/p) for p in (0.25,0.5,1,2.3)],
      rotor=rotor,packing=packing,
      free_body_peak_shift_mm=1000*0.030/(0.060+0.030)*0.004,
      gravity_torque_Nm=0.030*9.81*0.004,
      imu_bias_1mg_drift_1s_mm=1000*0.5*0.00981,
      attitude_0_1deg_lever50mm_um=1e6*0.050*math.radians(0.1),
      gravity_leak_0_1deg_drift_1s_mm=1000*0.5*9.81*math.sin(math.radians(0.1)),
      flexure_cycles_8Hz_2h_250days_3years=8*3600*2*250*3,
      i2c_read_9bytes_at_1MHz_us=9*9,
    )
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result

class IndependentChecks(unittest.TestCase):
    def test_contact_vector_projection(self):
        for t in (35,50,75):
            theta=math.radians(t)
            normal=0.15/math.sin(theta)
            # Project vertical normal into transverse plane, independently.
            actual=math.sqrt(normal**2-(normal*math.sin(theta))**2)
            self.assertAlmostEqual(actual,static_load(t)['transverse_N'],places=12)
    def test_power_from_current(self):
        a=static_load(50)
        kf=0.656*math.sqrt(2.47)
        i=a['actuator_force_N']/kf
        self.assertAlmostEqual(i*i*2.47,a['copper_W'],places=12)
    def test_half_force_quarters_heat(self):
        self.assertAlmostEqual(static_load(50,axial_force=0.075)['copper_W'] /
                               static_load(50)['copper_W'],0.25)
    def test_delay_against_time_domain(self):
        for f,tau in ((10,0.002),(8,0.01)):
            samples=20000
            ds=[math.sin(2*math.pi*k/samples)-
                math.sin(2*math.pi*k/samples-2*math.pi*f*tau) for k in range(samples)]
            rms=math.sqrt(sum(d*d for d in ds)/samples)
            self.assertAlmostEqual(rms*math.sqrt(2),residual(f,tau),places=11)
    def test_reaction_matches_second_difference(self):
        f,dt=8,1e-6
        x=lambda t:0.004*math.cos(2*math.pi*f*t)
        a=(x(dt)-2*x(0)+x(-dt))/dt**2
        self.assertAlmostEqual(abs(0.03*a)/reaction_force(f),1,places=5)
    def test_closed_motion_preserves_com(self):
        M,m=0.06,0.03
        for k in range(100):
            r=0.004*math.sin(2*math.pi*k/100)
            body=-m*r/(M+m)
            self.assertAlmostEqual(M*body+m*(body+r),0,places=14)
    def test_heat_against_euler_integration(self):
        power=2.68
        target=heat_time(power)
        temp,t,dt=25.,0.,0.001
        while temp<120:
            temp+=dt*(power-(temp-25)/100)/0.5
            t+=dt
        self.assertLess(abs(t-target),0.003)
    def test_momentum_energy_identity(self):
        r=generate()['rotor']
        self.assertAlmostEqual(r['energy_J'],r['momentum_Nm_s']**2/(2*r['inertia_kg_m2']))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentChecks)
    run=unittest.TextTestRunner(verbosity=2).run(suite)
    if not run.wasSuccessful():
        raise SystemExit(1)
    data=generate()
    data['verification']=dict(checks_run=run.testsRun,failures=len(run.failures),errors=len(run.errors))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'physics_results.json').write_text(json.dumps(data,indent=2)+'\n')
    for key in ('static','reaction','delay','battery','packing','thermal'):
        with (args.out/f'{key}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[key][0]))
            w.writeheader();w.writerows(data[key])
    print(json.dumps({k:data[k] for k in ('static','reaction','rotor','thermal','verification')},indent=2))

if __name__=='__main__':
    main()
