# Physics and control equations

Each equation has an identifier (P-n) and states where it is implemented and how it is verified. The last column of the table at the end gives the experiment that would **validate** it: tests show the code matches the equation; only experiments show the equation matches the pen. Notation follows `docs/icd.md` §1. Units are SI throughout.

## 1. Frames and kinematics

**P-1: basis.** In the page frame {P}:

- h = (cos φ, sin φ, 0)
- a = cos θ·h + sin θ·n
- t1 = sin θ·h − cos θ·n
- t2 = (−sin φ, cos φ, 0)
- x_H = cos ρ·t1 + sin ρ·t2
- y_H = −sin ρ·t1 + cos ρ·t2

Implemented in `stabpen/frames.py::basis`.

**P-2: tip displacement relative to the housing.** δ = q1·x_H + q2·y_H + s·a. Rev A adds the pivot-arc terms: axial retraction q²/(2L1) and nib rotation q/L1 (`pivot_second_order`).

**P-3: rigid-page Jacobian (the report's case).** Maintained contact, δ·n = 0, gives s = cot θ·q_t1 and

> Δ_page = J q,  J = Rot(φ)·diag(1/sin θ, 1)·Rot(ρ),  det J = 1/sin θ.

Implemented in `frames.jacobian`. Verified by `sim/tests/test_model.py::test_jacobian_analytic_matches_vector_construction` (analytic vs vector construction, 50 random orientations).

**P-4: compliance-aware Jacobian (COR-04).** When the housing is held compliantly, the tilt-plane stage motion splits between axial slide of the suspension and motion of the hand. The tilt-direction gain becomes

> J_t1 = sin θ + γ·cos²θ / sin θ,  γ = K_n sin²θ / (K_n sin²θ + k_ax),

where K_n is the normal stiffness the hand and pen present at the paper.

- γ = 1 recovers P-3.
- γ = 0 means the page absorbs nothing.

Implemented in `sim/pensim/core.py` (`Jt1`) and `model.build_params` (`gamma_acc`, computed from nominal compliances). The simulation effect of textbook vs compliance-aware Jacobian is in `results/sim/design_sweeps.json` (`jacobian`).

## 2. Contact mechanics

**P-5: paper reaction.** Take stroke direction β relative to h and friction coefficient μ. The friction components are f_h = −μN cos β and f_t2 = −μN sin β. Then

> R_t1 = −N cos θ + f_h sin θ,  R_t2 = f_t2,  R_a = N sin θ + f_h cos θ.

`stabpen/contact.py::reaction_components`.

**P-6: transverse stage load (COR-01).** The stage must carry

> |R⊥| = N·√((cos θ + μ cos β sin θ)² + (μ sin β)²).

The N cos θ term is quasi-static and dominates at writing altitudes. It is what the source report omitted.

- Frictionless check: |R⊥| = N cos θ (`test_transverse_load_limits`).
- In simulation, static holding force is within 1.5 % of P-6 at 35°, 50° and 75° (`results/sim/run_nominal.log`, "static").

**P-7: axial load.** F_a = N(sin θ − μ cos β cos θ) (`normal_from_axial` inverts it). The axial sensor measures F_a, not N, so the error of N̂ = F_a/sin θ depends on stroke direction. That error is up to μ·cot θ, about 37 % at 38° with μ = 0.3.

**P-8: normal compliance and pressure modulation.** Stage motion q_t1 changes the indentation by q_t1 cos θ. The resulting force modulation is ΔN ≈ k_eff·q_t1·cos θ, with k_eff the paper in series with the axial path and hand (`contact.pressure_modulation`). The source of the ink-tolerance question is EXP-B08.

**P-9: friction (LuGre, normalised by N).**

> ż = v − σ0|v|z/g(v),  g(v) = μk + (μs − μk)·exp(−(v/v_s)²),  f = −N(σ0 z + σ1 ż) − σ2 v.

Implemented in `core.py`. Verified by `test_friction_*` (stick, then kinetic plateau).

## 3. Stage, lever and suspension

**P-10: lever reduction (front pivot).** Pivot at L1 behind the ball, actuator line at L2 behind the pivot, n = L2/L1:

- tip-equivalent quantities: F_tip = n·F_act, x_act = n·x_tip, m_eq = J_pivot / L1²;
- carried-mass coupling to housing acceleration: m_couple = m_mov·L_cm / L1;
- geometric negative stiffness of order F_a / L1 from the axial load acting through the tilted lever.

**P-11: stage equation of motion (tip-equivalent, per housing axis).**

> m_eq q̈ + c_tip q̇ + k_tip q = F_act,tip + F_contact,x + F_stop(q) − m_couple a_H,x

- The stops are stiff springs and dampers beyond ±q_stop.
- The axial slide s obeys m_ax s̈ + c_ax ṡ + k_ax s = F_a − F_pre while the suspension is off its preload seat.

`core.py` integrates both at 25 µs with symplectic Euler. Verified by `test_free_vibration_*` (natural frequency and damping vs analytic) and the static-hold checks.

**P-12: flexures.**

- Cross-strip gimbal: bending stiffness k = E·w·t³/(12 L) per strip, referred to the tip through L1².
- Stress: σ = E·t·ψ/(2 L).
- Spiral-arm diaphragm: guided-cantilever arms.

`mechanics/flexure_calc.py` (results: gimbal 75.8 N/m at the tip, 177/82 MPa; diaphragm 1984 N/m, 231 MPa at the stop).

## 4. Hand

**P-13: two-stage hand impedance (HAP-26).** The pen barrel connects through the grip (k1 ‖ b1) to a hand mass M, which connects through the arm (k2 ‖ b2) to the imposed intended path:

> M ẍ_M = k1(x_H − x_M) + b1(ẋ_H − ẋ_M) − k2(x_M − x_ref) − b2(ẋ_M − ẋ_ref).

A separate normal stiffness and damping acts along n. Parameters are literature values measured in-plane without paper contact; γ and the normal values are EXP-B06 items.

## 5. Electromagnetic actuator and drive

**P-14: Lorentz actuator.** F = K_f·i with K_f = N_t·B·l_active. The motor constant is K_m = K_f/√R = B·√(V_cu·fill·(l_a/l_t)/ρ_cu), which does not depend on the winding (`actuator.motor_constant`).

**P-15: holding power.** P = (F_tip/(n·K_m))². Consequently:

- only the lever ratio and K_m reduce heat;
- rewinding changes only voltage and current: K_f ∝ √R and L ∝ R at fixed copper volume (DEC-012).

**P-16: coil electrical equation.** V = i·(R(T) + R_ext) + L di/dt + K_f·ẋ_act, with R(T) = R20·(1 + α_cu(T − 20 °C)).

- The drive is limited by duty ≤ 0.97 of VBAT.
- PWM ripple for drive/brake modulation has an exact exponential steady-state solution (`electronics/calcs/drive_sense.py::pwm_ripple`), cross-checked by ngspice (104 mA p-p at duty 0.72 in both).

**P-17: current loop.** A PI with its zero on the electrical pole gives open loop ω_c/s·e^(−sτ). The phase margin is 90° − 360°·f_c·τ, where τ is compute, zero-order-hold and anti-alias delay combined (47.5 µs at 40 kHz). The result is f_c ≈ 2.3 kHz at 50° margin.

## 6. Thermal

**P-18: lumped network.** The chain is coil → former/air gap → magnets and iron → barrel → hand/air. The source is P_cu(T), and coil resistance rises with temperature (feedback). `analysis/thermal.py` gives steady state and transients. With the 0.50 mm air gaps and 115 mW of electronics (v0.4.3): 96.6 °C coil and 34.1 °C surface at the design load (0.33 W average); allowable average copper loss 0.412 W, set by the 120 °C coil limit; runaway above it. Its two-node reduction (coil to structure 145 K/W with 0.22 J/K; structure to ambient 12.5 K/W with 14.9 J/K) is the firmware's thermal governor model. The simulator carries only the coil node (R_th, C_th): valid for its runs of seconds, which are much shorter than the structure's time constant (≈ 3 min).

## 7. Control and estimation

**P-19: stage servo (2 kHz).**

> F = K_p e + K_d ė_f + K_i ∫e + m_eq q̈_r + k_tip q_r + c_tip q̇_r − m_couple a_H

- Gains: K_p = m_eq ω_c² − k_tip, K_d = 2ζ m_eq ω_c, K_i = K_p ω_c κ_i (ω_c = 2π·60 Hz, ζ = 0.7, κ_i = 0.2).
- The derivative is filtered at 5 f_c.
- Current reference: i = −F/(n K_f).
- The measured-force contact feedforward N̂ cos θ is **disabled** (DEC-011; P-24).

**P-20: Kalman intent + oscillator (per page axis).**

- State: x = (p, v, a, x1, x2), where p, v, a is a white-jerk intended path and (x1, x2) is a damped oscillator at ω.
- Measurement: y = p + x1 + noise.
- Transition: F_int is the constant-acceleration block, and F_osc = r·[[cos ωT, sin ωT], [−sin ωT, cos ωT]] with r = e^(−T/τ_d).
- Noise: Q_int is the white-jerk covariance (spectral density q_j) and Q_osc = q_t T I.

Implemented in `core.py::_kf_step`, and ported to C in `firmware/`.

**P-21: frequency tracking, confidence and gate.**

- ω adapts from the oscillator phase rate, clipped to [ω_min, ω_max].
- Confidence comes from the filtered normalised innovation squared (NIS).
- Authority is g = g_max · conf · σ((f̂ − f_gate)/w_gate) · limits.
- The correction predicts the oscillator h ahead (h = sensor + half-period + servo + current-loop delays).

**P-22: page correction to stage command.** q_r = −g·J⁻¹(P-4)·d̂(t + h). It then passes through a radial soft limit with taper (q_lim 0.55 mm, 0.1 mm taper) and a slew limit (0.08 m/s).

**P-23: delay-limited cancellation bound.** A sinusoid cancelled with pure delay τ leaves a residual of |1 − e^(−jωτ)| = 2|sin(πfτ)|, which is 0.497 at 8 Hz and 10 ms. The source report's formula reproduces exactly. With servo dynamics the residual is larger (COR-07: 0.44 at 8 Hz for a 5 ms delay with a 60 Hz servo; `results/audit/fig_delay_residual_servo.png`).

**P-24: why the contact feedforward destabilised contact (DEC-011).**

- The feedforward is F_ff = cos θ·N̂.
- Through P-8, N follows the stage, so F_ff = cos²θ·K_n·H(s)·q. The physical reaction supplies −cos²θ·K_n·q instantly.
- With H a delay τ, the quadrature part acts as a damper of −cos²θ·K_n·sin(ωτ)/ω at the stage-against-paper mode, ω = √((m_eq ω_c² + cos²θ K_n)/m_eq).
- For the worst Monte Carlo sample this is 10.4 N·s/m of *negative* damping against 5.4 N·s/m of servo damping, at 183 Hz (`results/sim/ff_chatter.json`).

## 8. Evaluation definitions (simulation)

The **same-pen clean reference** is the same controller in neutral mode, on the same intended path, with no tremor. Residual metrics are computed only on samples where both runs are in contact, excluding ±30 ms around transitions:

- **ratio**: RMS ink error with the controller, divided by RMS ink error of the powered neutral pen.
- **distortion**: RMS ink difference between the controller and neutral on writing *without* tremor. This counts false corrections.
- **device distortion**: RMS ink difference between the neutral pen and a rigid pen, mean offset removed.
- **oracle**: cancels the instantaneous true housing disturbance, so it bounds what the mechanics can do.

## Model validation status

| Model | Implemented in | Verified by (code) | Validated by (experiment) | Acceptance for the model |
|---|---|---|---|---|
| Kinematics P-1…P-4 | `stabpen/frames.py`, `core.py` | analytic tests | EXP-B04 (Hall/optical vs motion stage) and EXP-B06 (γ) | Page displacement error < 5 % of stroke over θ 35–75° |
| Contact P-5…P-9 | `stabpen/contact.py`, `core.py` | limits, static check | EXP-B01 (3-axis load map) and EXP-B02 (friction vs speed) | Predicted \|R⊥\| within ±15 % across the map; LuGre fit R² > 0.9 |
| Stage/lever P-10…P-12 | `core.py`, `flexure_calc.py` | free-vibration, static | EXP-B05 (stage FRF, stiffness, stops) | Resonance within ±10 %; stiffness within ±15 % |
| Hand P-13 | `core.py` | — | EXP-B06 (grip impedance incl. normal direction, n ≥ 8) | Model FRF within the 10–90 % band of measured subjects |
| EM P-14…P-16 | `analysis/em_actuator.py`, `drive_sense.py` | ngspice cross-check | EXP-B03 (force–current–position map, R, L) | K_f(q) within ±10 %; K_m within ±10 % |
| Thermal P-18 | `analysis/thermal.py`, `core.py` | energy bookkeeping test | EXP-B07 (coil and skin temperature at 0.2–0.8 W) | Steady rise within ±15 %; time constant within ±25 % |
| Control P-19…P-24 | `core.py`, `firmware/` | servo tracking and oracle tests; C-vs-Python vectors | EXP-B09 (bench cancellation with injected disturbance) | Measured residual ratio within ±0.1 of the simulation for the same disturbance |
