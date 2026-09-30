# Mechanics audit and implemented redesign study

Evidence cut: 30 September 2026. Repository starting point: `4ad62b6`. All new results in this document are **calculations, proposed CAD, or simulations**. No mechanism was manufactured, no force or temperature was measured, and no handwriting improvement in a person was demonstrated. Historical results have been retained in their original directories; the new study is under `results/improvement/mechanics/`.

The useful outcome is a revised, testable fine-stage candidate and a separate grounded writing demonstrator. The fine stage expands usable mechanical radius from 1.0587 to 1.5 mm, with a proposed 24 mm body and approximately 152.3 mm overall length. Its larger working area is useful for stabilisation, but does not by itself establish normal-size automatic writing. The grounded demonstrator provides the larger force and travel needed to investigate explicitly accepted strokes. Combining the existing 12 mm inner-pen collar with the revised 24 mm fine stage without increasing sleeve diameter would be physically inconsistent.

## Findings that change the calculation

### Harmonic actuator load must retain phase

For prescribed sinusoidal displacement, the spring force and inertia oppose one another. The required force is

\[
F_{\rm rms}=q_{\rm rms}\sqrt{(k-m\omega^2)^2+(c\omega)^2}.
\]

The old balanced-nib calculation used the root sum of separately squared spring and inertia loads. This discarded their phase and falsely predicted a dynamic copper loss even at an undamped resonance. `bnib/loads.py` and the differentiable counterpart in `bnib/optimise.py` now use the coherent expression, including any balance-induced stiffness in the same term. A negative added stiffness can increase the inertial demand; it is not an independently positive RMS contribution. Independent time-domain tests integrate the force waveform and check the resonance limit.

This correction is not a claim that operating at resonance is a good handwriting controller. Contact, damping, changing frequency, delay, finite travel and transient force still matter. It corrects a specific power calculation.

### Straight wire leads acquire axial tension when deflected

The recorded Rev K suspension uses four nominal 0.10 mm wires of free length 26.801 mm. The stated anchor stiffness, 0.01 N/µm, is 10,000 N/m. For a fixed-guided wire translated laterally by \(q\), its neutral bending shape acquires approximately \(0.6q^2/L\) of arc length. A stiff axial anchor therefore adds tension, geometric stiffness and mean stress.

`revk/feasibility.py:wire_anchor` solves the beam-column shape and geometric compatibility self-consistently:

\[
P=P_0+K_{\rm series}\frac12\int_0^L(y')^2\,dz,
\qquad K_{\rm series}^{-1}=K_a^{-1}+\left(nEA/L\right)^{-1}.
\]

The displacement shape is the exact linear beam-column solution at the solved tension. Arc-length compatibility remains a second-order small-slope model; the studied \(q/L\) is below 0.1. The total elastic energy and force are independently checked by numerical differentiation. Bending reversal, the alternating half of geometric axial stress and mean axial stress are included in a conservative Goodman screen.

At the same 1.2587 mm hard stop, with the same four wires and material assumptions, changing only the anchor stiffness gives:

| Calculated quantity | 10,000 N/m anchor | 1,000 N/m anchor |
|---|---:|---:|
| Additional total axial tension | 0.3046 N | 0.0345 N |
| Lateral spring force | 18.20 mN | 3.89 mN |
| Anchor motion | 30.46 µm | 34.52 µm |
| Conservative Goodman factor | 1.075 | 1.881 |

Thus the original linear bending-only force of 1.97 mN at that displacement is not the loaded suspension force. A softer axial anchor is a substantive improvement. Its cable must be included in the stiffness budget: a flexible circuit that looks compliant can still dominate a 100 N/m target.

Material inputs are assumptions pending the actual wire grade, heat treatment, surface finish, termination and batch data: \(E=127.6\) GPa, UTS 1280 MPa, fatigue strength \(310\times0.85\) MPa. They are not a fatigue-life certificate for 0.10 mm soldered wires. Materion gives conductivity and modulus ranges for the alloy family and identifies 105 W/(m·K) thermal conductivity for hardened Alloy 25 rod/bar; using those values for the small wire is an explicit engineering assumption, not measured equivalence. [Materion high-strength copper-beryllium data](https://www.materion.com/en/products/performance-materials/high-performance-alloys/high-strength-copper-beryllium).

### Bearing preload produces force and heat even without external moment

The new opposed guide model contains six balls per race, two flat Hertz contacts per ball, unilateral loading and the specified 4 N preload per race. It solves axial and moment equilibrium and differentiates the contact law for stiffness. For the recorded worst moment, the calculation gives total normal load 8.072 N, maximum ball load 0.865 N, maximum Hertz pressure 2.640 GPa and minimum rotational stiffness approximately 626 N·m/rad. The calculated tilt is about 17.3 µrad **with rigid races and supports**.

Using the assumed rolling coefficient 0.001 gives approximately 8.07 mN drag, rather than estimating drag solely from the externally applied moment. The coefficient and race/support compliance remain unmeasured. Preload can improve stiffness while increasing friction, heat and fatigue loading; this is also the manufacturer's stated tradeoff. [NSK preload explanation](https://www.nsk.com/am-en/tools-resources/knowledge-center/bearing-abcs/preload/).

A preload spring does not by itself establish a drop rating. Its stiffness, available deflection, stop load path, contact deformation and impact duration are still needed. The new result therefore reports drop capacity as unknown.

### A physical workspace is a disk, and the page sees an ellipse

At fixed tilt \(\theta\) and zero roll, page displacement \(r\) maps to transverse nib displacement through

\[
q=M r,\qquad M=\operatorname{diag}(\sin\theta,1).
\]

A circular mechanical reach \(\|q\|\le T\) becomes an ellipse on the page, with semiaxes \(T/\sin\theta\) and \(T\). The refill's axial freedom maintains contact. The coordinate model is local and assumes a measured fixed pose; large attitude changes need a new map.

The existing `sim2j` command path already applies a radial page limit, so this audit does **not** assert that ordinary historic commands necessarily hit square corners. It does ensure that new field sweeps, clearance checks, accepted-writing plans and force allocation use one explicit radial envelope. Square per-axis limits would otherwise admit a corner \(\sqrt2\) times farther from the centre. The helper tests also verify virtual work, so forces transform by the transpose of the corresponding position Jacobian.

## Revised fine-stage candidate

The implemented search evaluates complete racetrack windings, their end turns, interlayer insulation, spatial cross-coupling and a signed six-component wrench per square root of copper power. The magnetic model is the existing analytical cuboid field with infinite-permeability image iron. It is an upper-bound approximation; the load study also applies an explicit 0.7 field multiplier. That factor is a sensitivity, not a confidence interval obtained from measurements.

Each candidate is selected by the minimum singular value of the in-plane force matrix over a sampled disk, rather than centre force alone. A second magnetic quadrature and denser disk refine the selected candidate. The search includes radii 1.0587, 1.5, 2, 2.5 and 3 mm. It does not report infeasible larger designs as successful optimisations.

The 1.5 mm proposal uses:

- A 24 mm body, 22 mm bore, 1.7 mm hard stop and 0.2 mm nominal travel reserve.
- Eight 0.10 mm BeCu lead/suspension wires, two in parallel per coil lead, with 34 mm free length. The added 7.199 mm is charged to the refill holder and body; it is not hidden in the existing envelope.
- A nominal total axial-anchor stiffness of 100 N/m and an 80–120 N/m target range, including cable and terminations.
- A four-beam stainless-steel anchor coupon with 6 mm beam length, 0.5 mm beam width and 0.035 mm thickness. Its calculated beam-only stiffness is about 76.6 N/m at assumed \(E=193\) GPa, leaving about 23.4 N/m for cable and other parallel stiffness. Thickness, boundary stiffness and cable response must be measured.
- Full circular guide races with a 7.55 mm ball-circle radius, 2.9 mm race width, 0.8 mm balls and 9.0 mm moving-flange radius. The front race is the hardened keeper surface in the proposed CAD, avoiding an overlapping duplicate plate.
- An approximately 3.67 g moving mass used for the new load study. This is an engineering mass estimate, not a weighed assembly.

The worst fatigue corner increases wire diameter by 2%, shortens the selected wire by 0.05 mm, raises modulus by 4%, uses 120 N/m anchor stiffness, permits 5 mN assembly tension and uses stress concentration factor 2.5. The calculated Goodman factor at the 1.7 mm stop is 1.696. Solder joints, corrosion, temperature dependence, out-of-plane motion and processing damage remain outside this fatigue calculation.

For the complete-ring guide and straight rearward lead topology, the necessary bore constraints imply approximately

\[
D_{\min}=8(T+0.2\ {m mm})+9.25\ {m mm}.
\]

This is a bound for this topology, not a universal bound on every pen mechanism. Changing to a different guide or moving the leads can alter it. It also is not a complete assembly collision certificate.

| Usable radius | Necessary body OD | Selected wire length | Worst fatigue factor | Minimum nominal \(K_m\) | Worst copper at 20 mN | At 40 mN |
|---|---:|---:|---:|---:|---:|---:|
| 1.0587 mm, reoptimised | 19.32 mm | 30 mm | 1.807 | 0.2302 N/√W | 0.0299 W | 0.0902 W |
| 1.5 mm | 22.85 mm | 34 mm | 1.696 | 0.1584 N/√W | 0.0809 W | 0.1890 W |
| 2.0 mm | 26.85 mm | 40 mm | 1.771 | 0.0794 N/√W | 0.4872 W | 0.8662 W |
| 2.5 mm | 30.85 mm | 45 mm | 1.773 | 0.0403 N/√W | 2.7993 W | 4.1374 W |
| 3.0 mm | 34.85 mm | 50 mm | 1.780 | 0.0261 N/√W | 10.2649 W | 13.8068 W |

All magnetic columns in this table use the **24 mm study body**. In particular the 2–3 mm field values are not simulations of already enlarged 27–35 mm bodies. The OD column explains why those candidates fail the present packaging; a larger-body optimisation would have to be rerun. The 1.0587 mm row is a new optimised candidate, not the unchanged historical baseline. The JSON separately preserves a matched original-winding/original-anchor load calculation.

Power is the worst average across 4, 8 and 12 Hz full-radius sinusoidal motion in eight directions, with a 0.7 field scale and the stated constant residual load. Nonlinear wire force, inertia, cross-coupled coil currents, hot resistance and reciprocal back-EMF are included. The 0.15 W copper allocation is assumed. Consequently the 1.5 mm candidate passes this particular 20 mN screen but fails the 40 mN screen. The useful gain is 41.7% radial travel, approximately twice the local page area, with a stated load limitation; it is not unrestricted larger handwriting authority.

Wire Joule heating is also checked. For a wire between equal-temperature clamps, with no convection,

\[
\Delta T_0=\frac{I_{\rm rms}^2\rho L^2}{8\kappa A^2},\qquad
\Delta T\approx\frac{\Delta T_0}{1-\alpha\Delta T_0}.
\]

The model includes positive resistivity feedback; cases without a finite equilibrium are flagged, not displayed as plausible temperatures. Reported temperature is rise above unknown clamp temperature. A 0.7 A transient driver limit is not a continuous rating for a single 0.10 mm lead. Parallel wires reduce each wire's current but require the added spring stiffness and package space already included above.

### An actual 20 mm body compaction screen

The 19.32 mm necessary diameter in the preceding table does not establish a complete pen of that diameter. A separate implementation, `revk/compact.py`, therefore resizes the stator, winding, guide, anchor and counter-face screen for an actual **20 mm outside diameter and 18 mm bore**, retaining 1.0587 mm usable radius and a 1.2587 mm stop. It computes a new 97-position magnetic map; it does not import the 24 mm design's force authority.

The selected complete winding clears the bore at the stop by 0.30 mm. The resized magnets are 3.706 mm square by 3.5 mm thick; the winding uses four insulated sublayers in `yxxy` order. The full-ring guide and eight-wire envelope fit, but their wire-circle radius has only a 0.340 mm allowable design interval. Fourteen of 248 counter-face candidates retain follower reserve and remain inside an 8.7 mm swept-radius limit. The selected counter-face reaches 8.290 mm swept radius and needs 4.031 mm positioner travel. These are geometric screens, not complete hinge or positioner solid models.

| Same usable radius and matched duty | 24 mm body calculation | Fresh 20 mm body calculation |
|---|---:|---:|
| Minimum nominal force constant over sampled disk | 0.2302 N/√W | 0.10284 N/√W |
| Worst average copper loss, 20 mN residual | 0.02988 W | 0.13857 W |
| Worst average copper loss, 40 mN residual | 0.09022 W | 0.41237 W |
| Worst average copper loss, 80 mN residual | 0.33155 W | 1.50758 W |

The duty comparison keeps the same estimated 3.57 g moving mass, 30 mm eight-wire suspension, 0.7 field sensitivity and 4/8/12 Hz motion assumptions. It isolates the resized winding and magnetic geometry rather than silently crediting a lower moving mass. At 20 mN the 20 mm candidate remains below the assumed 0.15 W copper allocation, but with only 7.6% headroom. At 40 mN it fails that allocation by a factor of 2.75, although its peak current and voltage remain below their electrical limits. At 80 mN both coil allocation and the wire-temperature screen fail. This design reduces outside diameter by 16.7% while paying a substantial force and heat penalty.

The smaller 6.212 mm ball-circle radius also lowers calculated rotational stiffness. Applying the same historical 10.874 mN·m nib moment gives 0.935 N maximum ball load, 2.710 GPa maximum Hertz pressure, approximately 349 N·m/rad minimum rotational stiffness and 31.0 µrad tilt with rigid races. This matched moment is not a complete new six-axis loaded-guide envelope, and no allowable contact stress or wear life has been verified. Resizing the axial-anchor coupon to a 5.146 mm beam length requires approximately 30.0 µm beam thickness for a 76.6 N/m beam contribution, again leaving 23.4 N/m nominal allowance for the cable. Processing and cable stiffness remain unknown.

The front cone is recomputed for 20 mm diameter. Its optical depth-of-field shortfall during ordinary handle lifts remains unresolved. Electronics, cell and PCB repackaging, hinge/positioner solids, joint stiffness, winding manufacture, full assembly collision checks and assembly access are also unresolved. Consequently `compact_20mm.json` explicitly reports a passing **component geometry screen** and an **unresolved whole-pen feasibility status**. The review figure is `compact_20mm_comparison.png`; there is no manufacturing-ready 20 mm assembly.

## Whole-pen translation and automatic writing

An internal translating mass can exert a transient or oscillatory reaction. It cannot sustain a DC force while remaining within bounded internal travel: \(F=m\ddot{x}\), so a nonzero constant force exhausts stroke quadratically with time. This is why a reaction mass may assist part of tremor suppression but cannot be the sole actuator for arbitrary accepted words against a static grip.

The repository's V2 collar is a worthwhile externally reacted idea: the fingers hold an outer collar while the inner pen pivots. But its approximately 21.7 mm diameter assumes a 12 mm moving pen. Replacing that with a 24 mm mechanism while preserving the same swing clearances implies at least approximately 33.7 mm sleeve diameter. The copied 0.656 N/√W actuator figure is also from another geometry, not a verified 12 mm end-face motor. This audit therefore does not promote the old collar's compactness and force assumptions into an achieved coarse/fine design.

The implemented alternative is a **grounded five-bar laboratory demonstrator**. Two motors and their bearings are fixed to a desk-mounted board. Two 60 mm proximal and two 90 mm distal links connect to a pen holder. The motor base spacing is 50 mm. A selected 60 × 40 mm workspace avoids kinematic singularities in a 425-point screen; the maximum sampled Jacobian condition number is 1.814.

The physical drive calculation uses the Faulhaber 2224 U 012 SR manufacturer's values: 6.21 mN·m continuous rated torque, 14.6 mN·m/A torque constant, 8.77 Ω resistance, 203 µH inductance and 2.7 g·cm² rotor inertia. Each motor is about 22 × 24.2 mm and 46 g. These motors remain on the board. Proposed 6:1 transmissions and 80% efficiency are design assumptions, and separate output bearings carry the linkage loads. [Faulhaber 2224 SR data sheet](https://www.faulhaber.com/fileadmin/Import/Media/EN_2224_SR_DFF.pdf).

`wholepen/grounded.py` derives the Jacobian from differentiated circle closure and transforms forces through \(\tau=J^TF\). Continuous torque produces a calculated minimum force disk of 0.480 N over the sampled workspace. The controller is limited to 0.4 N as an assumed interaction cap, not a clinically established safe force. An 80 g payload, 6/8 g proximal/distal links and reflected motor inertia yield Cartesian effective-mass eigenvalues from 93.2 to 104.6 g. Motor shaft speed, hot resistive voltage, back-EMF and sampled inductive voltage are included in trajectory postchecks. Elasticity, backlash, transmission wear and current-loop bandwidth require hardware work.

This is an academically grounded architecture direction, not evidence that a custom board already meets its requirements. A published Haply pantograph/digital-pen proof of concept demonstrates physical virtual-wall guidance of handwriting-like strokes over a much larger workspace; it does not demonstrate Parkinson's tremor elimination or reliable spelling correction. [PAL proof-of-concept paper](https://doi.org/10.3389/frobt.2021.700465). Commercial haptic hardware is another possible validation platform, but advertised peak force is not a guarantee at every pose or direction. [Haply Inverse3 specification](https://www.haply.co/inverse3), [manufacturer force-scaling explanation](https://docs.haply.co/docs/developing-with-inverse3/).

A moving-paper XY platen is a credible comparison for the next experiment. It generates relative ink motion without requiring the hand to follow the stroke, so it can avoid a major grip-force penalty. It instead moves the paper, requires a registered sheet and controlled nib contact/lift, can drag under the resting hand, and needs a footprint and paper clamp. The five-bar was chosen here because it can use the existing pen and explicitly measures the hand-interaction problem. A passive, slim stylus attached to an external stage could be sleeker than the active 24 mm pen; its tremor/contact behaviour and writing feel would require a separate study.

## Accepted trajectory integration

`wholepen/grounded_replay.py` consumes the writing agent's accepted-reference NPZ files, including exact position, velocity and acceleration. It preserves the fine/coarse inertial reaction through

\[
H=\begin{bmatrix}M_c+mI&mA\\mA^T&mA^TA\end{bmatrix},
\quad A=M^{-1},\quad r=c+Aq.
\]

Thus moving the body does not make the nib's absolute inertia disappear. The fine-stage force uses the transpose of the page-to-mechanical inverse under virtual work. The full winding matrix allocates currents with back-EMF and hot resistance, while the five-bar allocates force within its continuous motor torque and interaction cap. The simulation includes delayed noisy positions, filtered causal velocity estimates, nonlinear wire force, guide drag, an assumed hand spring/damper, finite lift delay and a latched refusal state. The current loops, rigid linkage and binary delayed contact are idealised.

The `lower` phase begins lowering before an ink stroke; the `lift` phase begins retraction while the tip remains stationary. Requested ink is never used as a substitute for actual modelled contact. The final physical comparison uses a 200 ms lift/lower assumption associated with the existing head, and retains any faster-lift scenario only as a labelled hypothetical external lifter. Delay and tracking failures must remain in the denominator. Stopping cannot be described as successful writing merely because the few surviving ink samples have low error.

The fine-loop bandwidth is frozen at 25 Hz from an independent discrete local pole screen, with the coarse loop at 9 Hz. Twenty-four combinations of mass scale 0.8/1.0/1.2, fine drag 0/0.2/2/8 N·s/m and coarse drag 0/80.2 N·s/m remain locally stable at the specified 0.5 ms step, 2 ms position delay and 100 Hz velocity filter. At 45 Hz, an unstable local pole and a saturated limit cycle were found; those diagnostics are retained under `diagnostic_45Hz/`. This screen excludes grip stiffness, nonlinear friction transitions, flexible modes, driver dynamics and attitude changes. It is a limited design check, not a global stability proof. A noise-free step-halving check reduced the accepted-`e` requested-ink RMS from approximately 0.04881 to 0.04852 mm, a 0.6% difference.

An independent friction-only check also examines the velocity step itself. The grounded fine guide has maximum differential drag 8 N·s/m; coarse drag including the resisting-hand damping is bounded by 80.8 N·s/m. For a fixed positive-definite coupled mass matrix, the explicit friction step cannot increase kinetic energy when \(\Delta t\,\lambda_{\max}(D_{\max},H)\le2\). Across the 425 sampled workspace points, the largest eigenvalue is 2316.97 s⁻¹, giving a 0.863 ms limit. The actual 0.5 ms step has a product of 1.1585. All 20,200 sampled nonlinear velocity updates and three free-decay checks remain dissipative. The fastest near-zero mode can alternate sign, so this is an energy/stability check rather than an accuracy certificate. All 80 final traces remain inside the sampled patch. `grounded_friction_check.json` records these checks and comparison with an independent implicit Radau solution; changing inertia, closed-loop forcing, springs and impacts are outside this isolated bound.

The final resisting-hand model is neutral at the actually placed starting pose. This avoids artificially preloading it by measuring spring deflection from the word patch centre. A separate diagnostic retains the earlier centre-neutral assumption. Both external resistance and the delayed lift matter: refusal after writing begins can leave incomplete or erroneous ink during retraction. A physical radial-stop collision is modelled as a dissipative impulse through the coupled mass matrix and explicitly counted as a failed safety target, not additional control authority.

For the accepted `e` with 200 ms lift/lower phases, the inverse-dynamics screen finds approximately 0.140 A coarse peak current, 1.46 V including sampled inductive voltage and 0.0719 W average coarse copper loss. The fine map requires approximately 0.0695 A peak, 0.0160 W average copper and 1.08 K maximum steady lead rise above clamps. Those values describe that one accepted reference under the specified load assumptions, not all writers or arbitrary words. Final replay and batch JSON files contain the actual-contact metrics, coverage and refusals; the final reference provenance and lift duration must be read alongside those numbers.

### Final coupled 20-writer result

The final batch consumes all 20 exported UJI session-1 template suffixes, each spelling the explicitly accepted future text `se`, at 3 mm x-height. It includes 200 ms lowering/lifting and a commanded 500 ms pen-up transfer between letters. There are 20 attempted suffixes and 40 letters **per condition**. These are synthetic acceptances using templates already present in the project, not a newly blinded test and not traces collected from people using this mechanism.

The declared engineering criterion is: no refusal or hard-stop collision, at least 98% requested-ink time with actual modelled contact, at most 0.10 mm RMS error while requested ink actually contacts, and at most 0.02 mm path length of ink during an air-transfer phase. These thresholds are design assumptions, not validated clinical readability thresholds.

| Coupled condition | Completed / attempted suffixes | Refused | Median ink coverage | Median RMS during actual requested ink | Stop-hit suffixes |
|---|---:|---:|---:|---:|---:|
| Feedback only, no resisting spring | 0 / 20 | 20 | 21.94% | 0.796 mm | 0 |
| Feedforward + feedback, no resisting spring | 20 / 20 | 0 | 100% | 0.03975 mm | 0 |
| Feedforward + feedback, 200 N/m start-neutral grip | 0 / 20 | 20 | 28.16% | 0.968 mm | 0 |
| Feedforward + feedback, 500 N/m start-neutral grip | 0 / 20 | 20 | 26.24% | 0.944 mm | 0 |

Every condition has ink in all 20 traces, so its error median also has a 20-word denominator. The low-stiffness successful condition reaches at most 0.2925 N coarse force and 0.11384 A fine-coil current. It demonstrates a conditional path to executing accepted future strokes in this proposed rigid mechanism model. The resisting-grip conditions fail the writing objective and the desired clean-abort behaviour: stopping the reference and requesting lift does not instantly remove a nib that takes 200 ms to retract. Their partial erroneous ink is an **unmet safety and quality target**, despite no hard-stop collision in this final gain/initialisation run. One hard-stop collision in the earlier 45 Hz diagnostic remains recorded rather than deleted.

**The 20/20 result does not establish actual acceleration or jerk compliance.** The declared completion criterion above did not contain those limits. A separate postprocessing check of every unloaded trace reconstructs velocity exactly from the semi-implicit position increments, then acceleration from the velocity increments. The initial position and zero velocity are known, and none of these traces has a stop projection. Sixty independent checks against the saved actuator forces and coupled mass matrix agree within \(8.21\times10^{-13}\) m/s². The source saves post-step states at pre-step labels; their reconstructed state time is the stored label plus 0.5 ms.

| Coordinates, all 20 unloaded suffixes | Maximum speed | Maximum acceleration | Maximum sampled jerk | Suffixes passing both 2 m/s² and 300 m/s³ comparisons |
|---|---:|---:|---:|---:|
| Combined tip on page | 32.003 mm/s | 3.69575 m/s² | 8064.39 m/s³ | 0 / 20 |
| Moving body on page | 23.692 mm/s | 2.45293 m/s² | 3507.87 m/s³ | 0 / 20 |
| Fine stage in mechanical axes | 9.276 mm/s | 2.50595 m/s² | 8615.18 m/s³ | 0 / 20 |

These are unfiltered norms of vector derivatives at the stored 0.5 ms step. The tip's median per-word peak acceleration is 2.96317 m/s²; during requested ink alone its maximum sampled jerk remains 7958.15 m/s³, so excluding startup or pen-up intervals does not resolve the violation. All 20 tip and fine-stage traces fail both comparisons; 11 body traces pass the acceleration comparison, but none passes the jerk comparison. The 2 m/s² and 300 m/s³ numbers are reference-planning assumptions, not measured device ratings, and page-tip, body and fine mechanical coordinates are distinct.

Sampled jerk here means adjacent acceleration-vector differences divided by 0.5 ms. Perfect current loops permit force changes at every control update; without a current-slew model these data do not certify a continuous-time jerk bound. The contact flag in this plant gates ink only: guide drag and balance bias remain active continuously, and no landing impact or contact-onset force jump is modelled. Differences coincident with contact-flag changes are recorded separately in `grounded_derivative_check.json` and must not be interpreted as impact estimates. Low path RMS and dissipative friction integration therefore do not establish acceptable actual motion dynamics. Meeting such bounds requires a separate actuator/sensing/control design and new validation.

Before automatic writing can be tested with a person, the design needs an independently verified admission test for measured hand resistance, enough force margin over the accepted path, and a fast, positively sensed ink-disengagement method. A moving-paper platen or a passive stylus on an external stage may avoid some of the force-against-grip problem. This simulation does not justify forcing a writer's hand through a word, and it does not establish that a compact pen alone can execute the same stroke.

The final evidence is `grounded_batch.json`, its 80 trace files under `grounded_words/`, and `grounded_batch_summary.png`. `grounded_replay.json` holds the separate single-letter gain/step-size checks. `grounded_servo_design.json` holds the independent local gain screen. Earlier 45 Hz and patch-centre-neutral runs are explicitly diagnostic and do not replace the final denominators.

## Reproducibility and retained provenance

The clone initially lacked ignored optimisation and calibration caches. `bnib/sim.py` now loads the recorded B1 geometry from committed study results when the transient optimisation cache is absent, rather than silently using a different hand-selected geometry. The calibration loader uses a committed versioned snapshot or raises an explicit error.

The original nine magnetic fit coefficients were uniquely recovered from 632 committed geometry/power observations. The recovery system has rank 9 and maximum log residual about \(6.7\times10^{-15}\). The correction for the old harmonic-power expression is explicitly inverted during recovery. Fifty newly computed magnetic cases independently check the recovered fit: RMS relative error 0.608%, maximum 1.333%. The recorded B1 geometry then reproduces \(K_m=0.400069981693\) N/√W. This is a reconstruction of historical calibration provenance, not a new performance result or measured motor constant. A separate fresh fit and its held-out cases are retained in `bnib/data/vc_calibration_refit.json`.

The new mechanics tests cover energy derivatives, geometric compatibility, Hertz equilibrium and stiffness, radial reach, electrical reciprocity and common force scaling. The grounded tests independently solve circle intersection for forward kinematics, check finite-difference Jacobians and virtual work, verify positive kinetic energy and the Coriolis energy identity, and test rated force limits. Additional tests check dissipative stop reactions, the frozen local gain corners and voltage allocation at the rail including friction current and an infeasible back-EMF case. The repository's overall test report is maintained by the coordinating audit.

Reproduction commands, using the repository environment:

```sh
python -m revk.improve
python -m revk.compact
python -m mechanics.cad.improved_nib
python -m wholepen.grounded --trajectory results/improvement/writing/coarse_fine_reference_200ms.npz
python -m wholepen.grounded_replay --trajectory PATH_TO_FINAL_200MS_REFERENCE
python -m wholepen.grounded_replay --batch results/improvement/writing/grounded_accepted/manifest.json
python -m wholepen.grounded_servo_design
python -m wholepen.grounded_friction_check
python -m wholepen.grounded_derivative_check
python -m mechanics.cad.grounded_stage
python -m revk.improvement_figures
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest revk/tests bnib/tests wholepen/tests/test_grounded_fivebar.py -q
```

`--reuse-fields` on the mechanics study reuses only that new study's stored magnetostatic maps and records this in provenance; load, wire and thermal calculations are rerun. Original results are not overwritten. The STEP files are reviewable proposed layouts with explicit keep-outs and unresolved joints, wire routing, sensing, supports and lift mechanics. They are not manufacturing-ready assemblies.

The next decision should be made from measured coupons and a grounded accepted-writing experiment: force maps over the loaded disk, current and temperature at steady duty, wire/anchor stiffness and fatigue, race friction and tilt under preload, lift timing and ink traces, and an output-encoder validation of the coarse stage. Those measurements decide whether the compact fine stage remains useful, whether the grounded mode provides enough writing benefit, and whether a slim passive stylus or a larger hand-reacted collar deserves the next design cycle.
