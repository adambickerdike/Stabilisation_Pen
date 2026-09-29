"""Proposed evidence-ledger rows of study V (header of docs/evidence.csv, 23 columns).

Primary sources: only those study V opened (full text, or the abstract when marked 'abstract only'); retrieved
2026-09-28.  Derived rows (this study's simulations) take their numbers from the stage results at report time.
"""
from __future__ import annotations

from typing import Dict, List

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
          "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator", "limitations",
          "relevance_to_design", "transferability", "transferability_reason", "design_implication", "retrieved", "search_query",
          "stream", "lead_verification"]

RET = "2026-09-28"


def _r(**kw) -> Dict[str, str]:
    row = {k: "" for k in HEADER}
    row.update({k: str(v) for k, v in kw.items()})
    row.setdefault("retrieved", RET)
    if not row["retrieved"]:
        row["retrieved"] = RET
    return row


PRIMARY: List[Dict[str, str]] = [
    # ------------------------------------------------------------------ MuJoCo and contact models
    _r(id="CON-53", topic="Physics engine: MuJoCo formulation and speed",
       citation="Todorov E, Erez T, Tassa Y. MuJoCo: A physics engine for model-based control. IEEE/RSJ IROS 2012", year=2012,
       doi_or_url="https://doi.org/10.1109/IROS.2012.6386109 ; https://roboti.us/lab/papers/TodorovIROS12.pdf",
       source_type="conference", evidence_class="numerical simulation", access_level="full text",
       task_or_setup="Engine description: generalized coordinates, recursive algorithms, velocity-stepping contact dynamics; timing benchmarks",
       participants_or_bench="Simulated humanoid (18 DOF, 6 active contacts) on a 12-core machine", comparator="Real time; ODE time steps",
       key_quantitative_findings="About 400,000 dynamics evaluations per second on 12 cores for an 18-DOF humanoid with 6 active contacts; stable at 15 ms time steps (about 5000 times faster than real time in that setting); ODE needed steps below 1 ms",
       units_and_conditions="evaluations/s; ms time step; 2012 hardware",
       locator="Abstract and performance section (author PDF)",
       limitations="Speeds are for a coarse humanoid; no accuracy statement for millimetre-scale friction; engine has changed since 2012",
       relevance_to_design="Choice of engine for simulator v2 (sim2)", transferability="medium",
       transferability_reason="Same engine family (MuJoCo 3.6), very different scale and time step (25 us)",
       design_implication="Speed must be re-measured for the pen model at 25 us (sim2 env benchmark); do not assume the paper's speed",
       search_query="Todorov Erez Tassa 2012 MuJoCo physics engine model-based control pdf", stream="CON"),
    _r(id="CON-54", topic="MuJoCo soft-constraint contact dynamics (convex, invertible)",
       citation="Todorov E. Convex and analytically-invertible dynamics with contacts and constraints: Theory and implementation in MuJoCo. IEEE ICRA 2014",
       year=2014, doi_or_url="https://doi.org/10.1109/ICRA.2014.6907751 ; https://roboti.us/lab/papers/TodorovICRA14.pdf",
       source_type="conference", evidence_class="numerical simulation", access_level="full text",
       task_or_setup="Complementarity-free soft constraints for all constraint types (contacts, limits, equality, friction); inverse dynamics",
       participants_or_bench="Simulated 27-DOF humanoid with 10 contacts", comparator="Complementarity (LCP) formulations",
       key_quantitative_findings="Forward dynamics of a 27-DOF humanoid with 10 contacts in about 0.1 ms; stable at 10 ms steps (about 100x real time on one core); analytic inverse dynamics. Author: 'All contact models presently used in rigid-body simulations are phenomenological, and the only way to validate them is to measure the contact interactions ... which is rarely done.'",
       units_and_conditions="ms per evaluation; single core", locator="Abstract; sections on soft constraints and performance",
       limitations="No experimental validation of friction at micrometre scale",
       relevance_to_design="Explains why sim2's native contacts creep and need calibration (EXP-V01)", transferability="high",
       transferability_reason="Same contact model as MuJoCo 3.6 native contacts",
       design_implication="Treat native contact parameters as phenomenological; calibrate against a measured pen-on-paper friction curve",
       search_query="Todorov convex analytically invertible dynamics contacts MuJoCo ICRA 2014 pdf", stream="CON"),
    _r(id="CON-55", topic="Simulator comparison: accuracy-speed trade-off",
       citation="Erez T, Tassa Y, Todorov E. Simulation tools for model-based robotics: Comparison of Bullet, Havok, MuJoCo, ODE and PhysX. IEEE ICRA 2015",
       year=2015, doi_or_url="https://doi.org/10.1109/ICRA.2015.7139807 ; https://roboti.us/lab/papers/ErezICRA15.pdf",
       source_type="conference", evidence_class="numerical simulation", access_level="full text",
       task_or_setup="Consistency-violation (self-consistency) measure versus speed across engines and time steps",
       participants_or_bench="Benchmark models (robotics and gaming tasks)", comparator="Five physics engines",
       key_quantitative_findings="Introduces a self-consistency measure (no ground truth needed); MuJoCo best on the robotics-related tests, gaming engines best on the gaming tests; speed-accuracy curves depend on time step",
       units_and_conditions="Qualitative ranking from speed-accuracy curves", locator="Abstract; results section",
       limitations="Authors are MuJoCo's developers; no frictional micro-sliding test",
       relevance_to_design="Method for sim2's calculation verification (time-step convergence against the finest step)", transferability="medium",
       transferability_reason="Method transfers; ranking may not", design_implication="Report convergence against step refinement, not only against another model",
       search_query="Erez Tassa Todorov 2015 simulation tools model-based robotics comparison pdf", stream="CON"),
    _r(id="CON-56", topic="Regularised (MuJoCo-type) contact: slip during stiction; physical compliance mapping",
       citation="Castro A, Permenter F, Han X. An unconstrained convex formulation of compliant contact. IEEE Transactions on Robotics (arXiv 2110.10107v2)",
       year=2022, doi_or_url="https://arxiv.org/abs/2110.10107", source_type="journal", evidence_class="numerical simulation",
       access_level="full text", task_or_setup="Convex compliant contact (SAP) versus regularised Anitescu/MuJoCo formulations",
       participants_or_bench="Simulated test cases", comparator="MuJoCo-type regularisation",
       key_quantitative_findings="Regularised formulations 'can lead to a noticeable non-zero slip velocity even during stiction'; MuJoCo contact is 'parameterized by a daunting number of non-physical parameters ... at the expense of drift'; SAP maps regularisation to physical compliance; gliding (normal separation while sliding) of order (dt + tau) mu |v_t|",
       units_and_conditions="Model statements", locator="Sections on related work and regularisation",
       limitations="Simulation study; no pen-on-paper case", relevance_to_design="Predicts the creep and gliding artefacts measured in sim2's native contact tests",
       transferability="high", transferability_reason="Applies to the MuJoCo contact model used by sim2",
       design_implication="Use a compliant penalty + LuGre law for micrometre ink studies; keep native contacts for coarse RL runs",
       search_query="Castro Permenter Han unconstrained convex formulation compliant contact arXiv", stream="CON"),
    _r(id="CON-57", topic="Contact models compared: tangential compliance relaxes Coulomb friction",
       citation="Le Lidec Q, Jallet W, Montaut L, Laptev I, Schmid C, Carpentier J. Contact models in robotics: a comparative analysis. IEEE Transactions on Robotics (arXiv 2304.06372v3)",
       year=2023, doi_or_url="https://arxiv.org/abs/2304.06372", source_type="journal", evidence_class="numerical simulation",
       access_level="full text", task_or_setup="Unified comparison of NCP, CCP (MuJoCo), relaxed and compliant models on test cases",
       participants_or_bench="Simulated benchmarks", comparator="Contact models and solvers",
       key_quantitative_findings="MuJoCo sets the regulariser R = alpha diag(G) with alpha near 0 (non-physical); 'adding compliance to the tangential components induces the vanishing of dry friction, resulting in tangential oscillations instead of a null velocity'; normal forces vary linearly with the compliance R",
       units_and_conditions="Model statements", locator="Sections on MuJoCo's formulation and on compliance",
       limitations="Robotics benchmarks, no writing", relevance_to_design="Explains the pen-sliding chatter and stick creep found with native contacts",
       transferability="high", transferability_reason="Same contact model", design_implication="Do not tune native contacts by eye; verify stick, slip and chatter per setting",
       search_query="Le Lidec contact models in robotics comparative analysis arXiv", stream="CON"),
    _r(id="CON-58", topic="MuJoCo computation: soft constraints, cones, integrators",
       citation="MuJoCo documentation, 'Computation' chapter (mujoco.readthedocs.io, stable)", year=2026,
       doi_or_url="https://mujoco.readthedocs.io/en/stable/computation/index.html", source_type="documentation",
       evidence_class="manufacturer statement", access_level="full text (summary tool)",
       task_or_setup="Reference documentation", participants_or_bench="n/a", comparator="n/a",
       key_quantitative_findings="Constraint reference acceleration a_ref = -b v - k r; solimp impedance d(r) and regulariser R; elliptic and pyramidal cones; soft contacts allow simultaneous positive force and velocity (slip, creep); noslip solver as post-processing; integrators Euler (implicit joint damping), implicit, implicitfast (drops Coriolis derivatives; recommended), RK4; explicit stability h < 2/omega_max",
       units_and_conditions="Definitions", locator="Sections Constraint model, Solver, Integrators",
       limitations="Documentation, not validation", relevance_to_design="Settings of sim2 (integrator, cones, solref/solimp)",
       transferability="high", transferability_reason="Documents the engine version used", design_implication="implicitfast at 25 us; check energy and convergence per integrator",
       search_query="WebFetch mujoco.readthedocs.io computation", stream="CON"),
    _r(id="CON-59", topic="MuJoCo solver parameters (solref, solimp) formulas",
       citation="MuJoCo documentation, 'Modeling' chapter, section Solver parameters (mujoco.readthedocs.io, stable)", year=2026,
       doi_or_url="https://mujoco.readthedocs.io/en/stable/modeling.html", source_type="documentation",
       evidence_class="manufacturer statement", access_level="full text (summary tool)",
       task_or_setup="Reference documentation", participants_or_bench="n/a", comparator="n/a",
       key_quantitative_findings="b = 2/(d_w timeconst), k = d(r)/(d_w^2 timeconst^2 dampratio^2); negative solref (-stiffness, -damping): b = damping/d_w, k = stiffness d(r)/d_w^2; defaults solref (0.02, 1), solimp (0.9, 0.95, 0.001, 0.5, 2); refsafe keeps timeconst >= 2 timesteps; friction rows use impedance solimp[0] and k = 0",
       units_and_conditions="Definitions", locator="Section Solver parameters",
       limitations="Documentation", relevance_to_design="Closed forms used by sim2's contact verification (static stiffness, creep)",
       transferability="high", transferability_reason="Same engine", design_implication="Static stiffness k = m_eff d^2/((1-d) d_w^2 tau^2 zeta^2) and creep v = R f / b verified in sim2 (verification.json)",
       search_query="WebFetch mujoco.readthedocs.io modeling solver parameters", stream="CON"),
    # ------------------------------------------------------------------ handwriting motor control
    _r(id="CON-60", topic="Kinematic theory of rapid movements (delta-lognormal)",
       citation="Plamondon R. A kinematic theory of rapid human movements. Part I. Movement representation and generation. Biological Cybernetics 72:295-307",
       year=1995, doi_or_url="https://doi.org/10.1007/BF00202785", source_type="journal", evidence_class="analytical derivation",
       access_level="abstract only", task_or_setup="Theory: agonist and antagonist neuromuscular systems with log-normal impulse responses",
       participants_or_bench="n/a (theory)", comparator="Observed velocity profiles (as stated in the abstract)",
       key_quantitative_findings="Log-normal impulse response follows from the central limit theorem over many interdependent neuromuscular networks; the delta-lognormal law 'can reproduce almost perfectly the complete velocity patterns of an end-effector' and accounts for invariance and rescalability of the patterns",
       units_and_conditions="Qualitative (abstract)", locator="Abstract (Europe PMC, PMID 7748959)",
       limitations="Abstract only; no parameter values", relevance_to_design="Basis of sim2's writer (sigma-lognormal, stabpen.signals)",
       transferability="medium", transferability_reason="Healthy rapid strokes; writing with tremor is outside the theory",
       design_implication="Writer kinematics are checked against measured speed and spectra (validation.json), not assumed",
       search_query="Europe PMC: kinematic theory of rapid human movements Plamondon 1995", stream="CON"),
    _r(id="CON-61", topic="Sigma-lognormal multi-level representation of handwriting strokes",
       citation="Plamondon R, Djioua M. A multi-level representation paradigm for handwriting stroke generation. Human Movement Science 25(4-5):586-607",
       year=2006, doi_or_url="https://doi.org/10.1016/j.humov.2006.07.004", source_type="journal", evidence_class="analytical derivation",
       access_level="abstract only", task_or_setup="Nested models of the Kinematic Theory (delta-lognormal, sigma-lognormal)",
       participants_or_bench="n/a", comparator="n/a",
       key_quantitative_findings="Nested lognormal models describe trajectory and velocity of strokes at several levels of representation (no numbers in the abstract)",
       units_and_conditions="Qualitative", locator="Abstract (Europe PMC, PMID 17023083)", limitations="Abstract only",
       relevance_to_design="Model family of sim2's intended-path generator", transferability="medium",
       transferability_reason="Model description, not population data", design_implication="Keep the writer parametric (stroke timing, amplitude) so it can be fitted to recorded writing",
       search_query="Europe PMC: multi-level representation paradigm handwriting stroke generation", stream="CON"),
    _r(id="CON-62", topic="Digitised handwriting kinematics in healthy adults (method reliability)",
       citation="Mergl R, Tigges P, Schroeter A, Moeller HJ, Hegerl U. Digitized analysis of handwriting and drawing movements in healthy subjects: methods, results and perspectives. Journal of Neuroscience Methods 90(2):157-169",
       year=1999, doi_or_url="https://doi.org/10.1016/S0165-0270(99)00080-1", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="Digitising tablet; simple writing and drawing tests",
       participants_or_bench="Healthy subjects (number not in the abstract read)", comparator="Age, verbal intelligence, motor practice, handedness",
       key_quantitative_findings="Younger subjects write faster and with more automation; verbal intelligence and motor practice moderate kinematics; personality and gender little influence; no left/right-hander difference; high test-retest stability (no magnitudes in the abstract)",
       units_and_conditions="Qualitative (abstract)", locator="Abstract (Europe PMC record)", limitations="Abstract only; no numbers",
       relevance_to_design="Writer variability to randomise (age, practice)", transferability="medium",
       transferability_reason="Healthy adults on a tablet", design_implication="Randomise writing speed and automation per virtual writer",
       search_query="Europe PMC: Digitized analysis of handwriting and drawing movements in healthy subjects", stream="CON"),
    # ------------------------------------------------------------------ credibility (V&V)
    _r(id="CON-63", topic="Credibility of computational models in device submissions (FDA framework)",
       citation="U.S. FDA. Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions. Guidance for Industry and FDA Staff, 17 November 2023 (docket FDA-2021-D-0980)",
       year=2023, doi_or_url="https://www.fda.gov/media/154985/download", source_type="standard", evidence_class="standard",
       access_level="full text", task_or_setup="Regulatory guidance (nonbinding)", participants_or_bench="n/a", comparator="ASME V&V 40-2018",
       key_quantitative_findings="Nine steps: question of interest; context of use (COU); model risk = model influence x decision consequence; credibility evidence in 8 categories (code verification, model calibration, bench validation, in vivo validation, population-based validation, emergent model behaviour, model plausibility, calculation verification/UQ with COU simulations); credibility factors and prospective goals; adequacy assessment; report",
       units_and_conditions="Framework", locator="Sections IV-VI of the guidance PDF",
       limitations="Nonbinding; no numerical acceptance levels", relevance_to_design="Structure of sim2's credibility plan (docs/sim_v2.md section 8)",
       transferability="high", transferability_reason="The pen is a medical-device candidate; the framework is generic",
       design_implication="State COU and model risk before using sim2 results as design evidence; plan bench validation (EXP-V01..V06)",
       search_query="FDA assessing credibility computational modeling simulation medical device submissions guidance 2023 pdf", stream="CON"),
    _r(id="CON-64", topic="ASME V&V 40-2018 scope (credibility commensurate with model risk)",
       citation="ASME. V&V 40-2018 Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices (standard product page)",
       year=2018, doi_or_url="https://www.asme.org/codes-standards/find-codes-standards/assessing-credibility-of-computational-modeling-through-verification-and-validation-application-to-medical-devices",
       source_type="standard", evidence_class="standard", access_level="product page only (standard not read)",
       task_or_setup="Standard description", participants_or_bench="n/a", comparator="n/a",
       key_quantitative_findings="Framework for assessing the relevance and adequacy of completed V&V activities; credibility commensurate with 'the degree to which the computational model is relied on ... and the consequences of that decision being incorrect'; not a step-by-step guide and no quantitative credibility method",
       units_and_conditions="Scope statement", locator="ASME product page", limitations="Standard text not read (paywalled); FDA 2023 and Viceconti 2021 describe it",
       relevance_to_design="Credibility factors and goals in docs/sim_v2.md", transferability="high",
       transferability_reason="Written for medical devices", design_implication="Set credibility goals per factor proportional to model risk",
       search_query="ASME V&V 40-2018 standard page", stream="CON"),
    _r(id="CON-65", topic="Verification, validation and UQ of in silico models for regulatory use",
       citation="Viceconti M, Pappalardo F, Rodriguez B, Horner M, Bischoff J, Musuamba Tshinanu F. In silico trials: Verification, validation and uncertainty quantification of predictive models used in the regulatory evaluation of biomedical products. Methods 185:120-127",
       year=2021, doi_or_url="https://doi.org/10.1016/j.ymeth.2020.01.011 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC7883933/",
       source_type="journal", evidence_class="review", access_level="full text (PMC, via summary tool)",
       task_or_setup="Interpretation of ASME V&V 40 for in silico trials", participants_or_bench="n/a", comparator="EMA/FDA practice",
       key_quantitative_findings="Six steps grounded in V&V 40: COU; risk (influence x consequence); credibility goals; verification (code: find errors; calculation: estimate numerical error, refine discretisation, observed order of convergence); validation and UQ ('a model that agrees with experimental results but has high uncertainty in model form is suspect'); applicability ('the closer the validation activities are to the COU ... the more confidence'); sensitivity analysis for key parameters",
       units_and_conditions="Method", locator="Sections 2.1-2.6, 3.1, 4.2", limitations="Physics-based models in mind; ML extensions discussed with caveats",
       relevance_to_design="Observed-order check and applicability argument in sim2's V&V", transferability="high",
       transferability_reason="Same class of mechanistic models", design_implication="Report observed order of convergence; validate close to the COU (writing on paper with tremor)",
       search_query="Europe PMC: In silico trials verification validation uncertainty quantification Viceconti", stream="CON"),
    # ------------------------------------------------------------------ hand and arm impedance, muscle models
    _r(id="HAP-95", topic="Hand stiffness: spring-like, ellipse shape and orientation invariant",
       citation="Mussa-Ivaldi FA, Hogan N, Bizzi E. Neural, mechanical, and geometric factors subserving arm posture in humans. J Neurosci 5(10):2732-2743",
       year=1985, doi_or_url="https://doi.org/10.1523/JNEUROSCI.05-10-02732.1985", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="Torque motors displace the hand in the horizontal plane; restoring forces before voluntary reaction",
       participants_or_bench="Human subjects (number not in the abstract)", comparator="Postures, subjects, time",
       key_quantitative_findings="Stiffness represented as a matrix and an ellipse (area, axis ratio, major-axis direction); conservative component much larger than non-conservative (spring-like); shape and orientation invariant over subjects and time; voluntary changes mainly in magnitude, shape and orientation changed little",
       units_and_conditions="Horizontal plane; static hold", locator="Abstract (Europe PMC)", limitations="Abstract only; no values",
       relevance_to_design="Hand impedance anisotropy in sim2 and DR (per-axis arm stiffness)", transferability="medium",
       transferability_reason="Whole-arm posture, not a pen grasp", design_implication="Randomise impedance magnitude more than its shape",
       search_query="Europe PMC DOI:10.1523/JNEUROSCI.05-10-02732.1985", stream="HAP"),
    _r(id="HAP-96", topic="Task-dependent arm viscoelasticity; co-contraction changes the stiffness ellipse",
       citation="Gomi H, Osu R. Task-dependent viscoelasticity of human multijoint arm and its spatial characteristics for interaction with environments. J Neurosci 18(21):8965-8978",
       year=1998, doi_or_url="https://doi.org/10.1523/JNEUROSCI.18-21-08965.1998", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="Multijoint arm stiffness and viscosity under co-contraction and force tasks",
       participants_or_bench="Human subjects", comparator="Co-contraction ratio; hand position",
       key_quantitative_findings="Co-contraction ratio changes stiffness shape and orientation, especially at proximal hand positions; single-joint stiffness roughly proportional to its own joint torque; viscosity-torque relation similar",
       units_and_conditions="Horizontal arm", locator="Abstract (Europe PMC, PMID 9787002)", limitations="Abstract only",
       relevance_to_design="Co-contraction as a DR variable (MyoArm check)", transferability="medium",
       transferability_reason="Arm posture differs from writing", design_implication="Scale arm stiffness and damping together with co-contraction in DR",
       search_query="Europe PMC: Task-dependent viscoelasticity human multijoint arm", stream="HAP"),
    _r(id="HAP-97", topic="Endpoint elasticity rises with force; damping ratio nearly constant",
       citation="Perreault EJ, Kirsch RF, Crago PE. Multijoint dynamics and postural stability of the human arm. Exp Brain Res 157(4):507-517",
       year=2004, doi_or_url="https://doi.org/10.1007/s00221-004-1864-7", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="Stochastic position perturbations by a 2-link robot during isometric force regulation",
       participants_or_bench="Human subjects", comparator="Voluntary force level and direction",
       key_quantitative_findings="Endpoint elasticity increases nearly linearly with voluntary force; viscosity increases nonlinearly; 'remarkably consistent' damping ratio across subjects and conditions",
       units_and_conditions="Isometric tasks", locator="Abstract (Europe PMC, PMID 15112115)", limitations="Abstract only; no values",
       relevance_to_design="Constant damping ratio used for sim2's arm joints over co-contraction", transferability="medium",
       transferability_reason="Arm endpoint, isometric", design_implication="Keep zeta constant when randomising co-contraction (params.Arm.zeta)",
       search_query="Europe PMC: Multijoint dynamics and postural stability of the human arm", stream="HAP"),
    _r(id="HAP-98", topic="Index-finger stiffness anisotropy and co-contraction",
       citation="Milner TE, Franklin DW. Characterization of multijoint finger stiffness: dependence on finger posture and force direction. IEEE Trans Biomed Eng 45(11):1363-1375",
       year=1998, doi_or_url="https://doi.org/10.1109/10.725333", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="2-D static stiffness of the index finger, flexed and extended postures",
       participants_or_bench="Human subjects", comparator="Posture; force direction",
       key_quantitative_findings="Stiffness anisotropic; greatest stiffness roughly parallel to the proximal phalanx; no monotonic relation between joint stiffness and net torque (co-contraction matters)",
       units_and_conditions="Static", locator="Abstract (Europe PMC, PMID 9805835)", limitations="Abstract only; single finger",
       relevance_to_design="Finger-pad zone of the grip is anisotropic; MyoArm fingers linearised", transferability="medium",
       transferability_reason="Single finger, not a tripod pen grasp", design_implication="Allow anisotropic grip stiffness in DR (t1 vs t2)",
       search_query="Europe PMC: Characterization of multijoint finger stiffness", stream="HAP"),
    _r(id="HAP-99", topic="Learned impedance stabilises unstable dynamics",
       citation="Burdet E, Osu R, Franklin DW, Milner TE, Kawato M. The central nervous system stabilizes unstable dynamics by learning optimal impedance. Nature 414:446-449",
       year=2001, doi_or_url="https://doi.org/10.1038/35106566", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="Arm movements in an unstable force field (robotic interface)", participants_or_bench="Human subjects",
       comparator="Stable versus unstable dynamics",
       key_quantitative_findings="Subjects learned to stabilise unstable dynamics by selective, energy-efficient control of impedance geometry",
       units_and_conditions="Qualitative (abstract)", locator="Abstract (Europe PMC, PMID 11719805)", limitations="Abstract only",
       relevance_to_design="A writer adapts impedance to a device; the MyoArm posture is statically unstable without such control",
       transferability="medium", transferability_reason="Reaching, not writing", design_implication="Model the writer's impedance as adaptive (DR over co-contraction), and test device-induced changes (EXP-V04)",
       search_query="Europe PMC: central nervous system stabilizes unstable dynamics learning optimal impedance", stream="HAP"),
    _r(id="HAP-100", topic="MyoSuite musculoskeletal models in MuJoCo",
       citation="Caggiano V, Wang H, Durandau G, Sartori M, Kumar V. MyoSuite: A contact-rich simulation suite for musculoskeletal motor control. L4DC 2022 (arXiv 2205.13600)",
       year=2022, doi_or_url="https://arxiv.org/abs/2205.13600", source_type="conference", evidence_class="numerical simulation",
       access_level="full text", task_or_setup="Musculoskeletal models (MyoHand, MyoElbow, MyoFinger) converted from OpenSim; RL tasks",
       participants_or_bench="Simulated models", comparator="OpenSim moment arms and forces",
       key_quantitative_findings="MyoHand: 29 bones, 23 joints, 39 muscle-tendon units (from the MoBL and 2nd-hand OpenSim models); Hill-type muscles (force-length, force-velocity, passive), first-order activation, tendons infinitely stiff in MuJoCo; MyoSim pipeline optimises moment arms and forces against OpenSim; supports fatigue, sarcopenia, tendon transfer, exoskeletons",
       units_and_conditions="Model description", locator="Sections on models and MyoSim", limitations="Hill-type without short-range stiffness; no reflexes",
       relevance_to_design="MyoArm (installed MyoSuite 2.12.2: 38 joints, 63 muscles) used for sim2's hand-impedance check", transferability="medium",
       transferability_reason="Generic adult anatomy; muscle model lacks SRS", design_implication="Use MyoArm to scale impedance with co-contraction, not for absolute stiffness",
       search_query="MyoSuite contact-rich simulation suite musculoskeletal arXiv 2205.13600", stream="HAP"),
    _r(id="HAP-101", topic="Hill-type models underestimate short-range stiffness",
       citation="van der Zee TJ, Simha SN, Milburn GN, Campbell KS, Ting LH, De Groote F. Cross-bridge model for predicting muscle short-range stiffness during movement. PLOS Computational Biology 22(9):e1014748",
       year=2026, doi_or_url="https://doi.org/10.1371/journal.pcbi.1014748", source_type="journal", evidence_class="numerical simulation",
       access_level="full text (summary tool)", task_or_setup="Muscle models versus short-range stiffness data across activation, amplitude and recovery time",
       participants_or_bench="Muscle data sets (as used by the authors)", comparator="Hill-type versus cross-bridge models",
       key_quantitative_findings="Hill-type models 'do not capture the history dependence of short-range stiffness' and underestimate it at submaximal activation; relative SRS error RMSD 0.204 (Hill with series compliance) versus 0.103-0.104 (3- and 4-state cross-bridge); trials with large stiffness reductions 0.312 versus 0.101; stretch 3.83 % L0 at 0.45 L0/s; SRS window 10 ms",
       units_and_conditions="Normalised stiffness errors", locator="Results (Figure 6), Discussion, Abstract",
       limitations="Muscle level, not endpoint", relevance_to_design="Why MyoArm's small-perturbation stiffness is low and its posture unstable",
       transferability="high", transferability_reason="MyoSuite uses Hill-type muscles", design_implication="Do not take MyoArm static stiffness as the writer's; bench measurement needed (EXP-I01/V04)",
       search_query="short-range stiffness Hill-type muscle model underestimate cross-bridge PLOS", stream="HAP"),
    # ------------------------------------------------------------------ tremor physiology and models
    _r(id="PDT-53", topic="Tremor propagation in a 7-DOF upper-limb model",
       citation="Corie TH, Charles SK. Simulated tremor propagation in the upper limb: from muscle activity to joint displacement. J Biomech Eng 141(8):081001",
       year=2019, doi_or_url="https://doi.org/10.1115/1.4043442 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6528735/",
       source_type="journal", evidence_class="numerical simulation", access_level="full text (PMC, via summary tool)",
       task_or_setup="Linear 7-DOF model (SFE, SAA, SIER, EFE, FPS, WFE, WRUD), 15 superficial muscles; tremorogenic input 4-12 Hz",
       participants_or_bench="Model", comparator="Input distributions across muscles",
       key_quantitative_findings="Tremorogenic activity as a triangular pulse train (mean width 110 ms); with uniform input at 8 Hz the three distal DOF (FPS, WFE, WRUD) carry 83 % of tremor; the 6 distal forearm muscles cause 63 %; inertial coupling spreads tremor; adding inertia or viscoelasticity to the wrong DOF can increase tremor; not validated experimentally",
       units_and_conditions="4-12 Hz", locator="Model and Results sections", limitations="Linear, unvalidated",
       relevance_to_design="sim2 injects tremor torques at the forearm (pronation-supination) and wrist", transferability="medium",
       transferability_reason="Model study", design_implication="Tremor sources in sim2 are distal torques; test device effect with the arm model (validation.json)",
       search_query="Corie Charles simulated tremor propagation upper limb", stream="PDT"),
    _r(id="PDT-54", topic="Physiological vs pathological tremor: linear vs nonlinear dynamics",
       citation="Timmer J, Gantert C, Deuschl G, Honerkamp J. Characteristics of hand tremor time series. Biological Cybernetics 70(1):75-80",
       year=1993, doi_or_url="https://doi.org/10.1007/BF00202568", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="Time-series analysis of hand tremor recordings", participants_or_bench="Physiological, ET and PD tremor",
       comparator="Linear stochastic versus nonlinear models",
       key_quantitative_findings="Physiological and pathological tremor separated by linear versus nonlinear behaviour with error below 20 %; ET versus PD separated with error below 10 % using nonlinear measures",
       units_and_conditions="Classification error", locator="Abstract (Europe PMC, PMID 8312399)", limitations="Abstract only",
       relevance_to_design="sim2 models pathological tremor as a narrow-band oscillator with wander (nonlinear limit cycle), physiological tremor as broadband",
       transferability="medium", transferability_reason="Hand tremor recordings (no pen)", design_implication="Keep separate generator families for physiological and pathological tremor",
       search_query="Europe PMC: Characteristics of hand tremor time series", stream="PDT"),
    _r(id="PDT-55", topic="Physiologic tremor: mechanical-resonant and central components with age",
       citation="Elble RJ. Characteristics of physiologic tremor in young and elderly adults. Clinical Neurophysiology 114(4):624-635",
       year=2003, doi_or_url="https://doi.org/10.1016/S1388-2457(03)00006-3", source_type="journal", evidence_class="physical human study",
       access_level="abstract only", task_or_setup="Hand accelerometry and EMG, with and without 300 g loading",
       participants_or_bench="100 young (20-42 y) and 100 elderly (70-92 y) adults", comparator="Age; loading",
       key_quantitative_findings="EMG spectral peak 9-12 Hz in 8 young and 5-7 Hz in 5 elderly subjects; age had no effect on the mechanical-resonant component; about 8 % of controls had an EMG-acceleration pattern like mild ET",
       units_and_conditions="Postural hand tremor; 300 g load", locator="Abstract (Europe PMC, PMID 12686271)", limitations="Abstract only",
       relevance_to_design="Inertial loading test of sim2's arm model (wrist resonance shift)", transferability="medium",
       transferability_reason="Posture, not writing", design_implication="A pen or rear module that adds inertia shifts only the mechanical component",
       search_query="Europe PMC: Characteristics of physiologic tremor in young and elderly adults", stream="PDT"),
    _r(id="PDT-56", topic="Tremor phenomenology: frequency bands, amplitude, loading",
       citation="Hess CW, Pullman SL. Tremor: clinical phenomenology and assessment techniques. Tremor Other Hyperkinet Mov 2",
       year=2012, doi_or_url="https://doi.org/10.7916/D8WM1C41 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC3517187/",
       source_type="review", evidence_class="review", access_level="full text (PMC, via summary tool)",
       task_or_setup="Clinical review", participants_or_bench="n/a", comparator="Tremor types",
       key_quantitative_findings="Physiological tremor 8-12 Hz and higher, irregular, very low amplitude; PD rest 3-6 Hz; PD action 5-8 Hz with lower amplitude; ET 4-12 Hz, falling with age, typically 4-8 Hz; ET kinetic amplitude generally larger than postural; displacement measurable below 0.1 mm; inertial loading lowers the mechanical-reflex component, the central component is unaffected; re-emergent tremor has a delayed onset, ET does not",
       units_and_conditions="Hz; mm", locator="Sections on tremor types and quantitative assessment", limitations="Review",
       relevance_to_design="Ranges of sim2's tremor profiles (tremor.py) and DR f0 4-12 Hz", transferability="high",
       transferability_reason="Clinical ranges", design_implication="Profiles: ET 4-12 Hz, PD rest 3-6 Hz gated by movement, physiological 8-12 Hz",
       search_query="WebFetch PMC3517187 Hess Pullman tremor phenomenology", stream="PDT"),
    _r(id="PDT-57", topic="Real-time tremor estimation from gyroscopes",
       citation="Gallego JA, Rocon E, Roa JO, Moreno JC, Pons JL. Real-time estimation of pathological tremor parameters from gyroscope data. Sensors 10(3):2129-2149",
       year=2010, doi_or_url="https://doi.org/10.3390/s100302129 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC3264472/",
       source_type="journal", evidence_class="physical human study", access_level="full text (PMC, via summary tool)",
       task_or_setup="Two-stage tremor/voluntary separation from gyroscope data", participants_or_bench="5 patients (4 men, 1 woman), 48-74 y",
       comparator="Estimator variants",
       key_quantitative_findings="ET 4-7 Hz, PD rest 3-4 Hz, postural 6 Hz; voluntary tracking up to 2 Hz, daily-living movements 0.48-2.47 Hz; tremor estimate error 0.001 +/- 0.002 rad/s (Kalman filter)",
       units_and_conditions="rad/s; Hz", locator="Sections 2-4", limitations="5 patients; wearable gyros on the limb, not a pen",
       relevance_to_design="Voluntary/tremor band split used by sim2's writer and trackers", transferability="medium",
       transferability_reason="Limb-mounted gyros", design_implication="Voluntary writing below about 2-3 Hz; tremor estimation from pen gyros is plausible",
       search_query="WebFetch PMC3264472 Gallego real-time estimation tremor gyroscope", stream="PDT"),
    # ------------------------------------------------------------------ sim-to-real, DR, system identification
    _r(id="OPT-55", topic="Domain randomisation (visual) for sim-to-real",
       citation="Tobin J, Fong R, Ray A, Schneider J, Zaremba W, Abbeel P. Domain randomization for transferring deep neural networks from simulation to the real world. IEEE/RSJ IROS 2017 (arXiv 1703.06907)",
       year=2017, doi_or_url="https://arxiv.org/abs/1703.06907", source_type="conference", evidence_class="physical bench experiment",
       access_level="full text", task_or_setup="Object localisation trained only on randomised synthetic images", participants_or_bench="Real robot scenes",
       comparator="Real images", key_quantitative_findings="Detector accurate to about 1.5 cm trained only on simulated images with random textures; described as the first sim-only RGB transfer for robot control",
       units_and_conditions="cm localisation error", locator="Abstract; experiments", limitations="Vision, not dynamics",
       relevance_to_design="Principle of randomising what is uncertain", transferability="low",
       transferability_reason="Perception task", design_implication="Randomise sensor appearance/noise, not only dynamics",
       search_query="Tobin domain randomization arXiv 1703.06907", stream="OPT"),
    _r(id="OPT-56", topic="Dynamics randomisation: ranges and ablations",
       citation="Peng XB, Andrychowicz M, Zaremba W, Abbeel P. Sim-to-real transfer of robotic control with dynamics randomization. IEEE ICRA 2018 (arXiv 1710.06537)",
       year=2018, doi_or_url="https://arxiv.org/abs/1710.06537", source_type="conference", evidence_class="physical bench experiment",
       access_level="full text", task_or_setup="Pushing task with an LSTM policy trained in randomised simulation", participants_or_bench="Fetch robot, 28 real trials",
       comparator="Ablations of randomised parameters",
       key_quantitative_findings="95 randomised parameters (link mass 0.25-4x, joint damping 0.2-20x, puck mass 0.1-0.4 kg, friction 0.1-5, damping 0.01-0.2, table height 0.73-0.77 m, action time step with exponential jitter, observation noise); log-uniform sampling for mass, damping, friction, gains; real success 0.89 +/- 0.06 versus fixed time step 0.29, no observation noise 0.25, fixed link mass 0.64, fixed puck friction 0.48",
       units_and_conditions="Success rate", locator="Sections IV-V, Table", limitations="One task", relevance_to_design="sim2 DR uses log-uniform ranges and randomises timing and sensor noise",
       transferability="medium", transferability_reason="Robot arm, not a pen", design_implication="Randomise control latency and sensor noise; ablate DR factors before trusting a policy",
       search_query="Peng sim-to-real dynamics randomization arXiv 1710.06537", stream="OPT"),
    _r(id="OPT-57", topic="System identification + actuator/latency models + DR",
       citation="Tan J, Zhang T, Coumans E, Iscen A, Bai Y, Hafner D, Bohez S, Vanhoucke V. Sim-to-Real: Learning agile locomotion for quadruped robots. RSS 2018 (arXiv 1804.10332)",
       year=2018, doi_or_url="https://arxiv.org/abs/1804.10332", source_type="conference", evidence_class="physical bench experiment",
       access_level="full text", task_or_setup="Quadruped gaits learned in simulation with identified actuator and latency models", participants_or_bench="Minitaur robot",
       comparator="With and without system identification/randomisation",
       key_quantitative_findings="Randomisation ranges: mass 80-120 %, motor friction 0-0.05 N m, inertia 50-150 %, motor strength 80-120 %, control step 3-20 ms, latency 0-40 ms, battery 14.0-16.8 V, contact friction 0.5-1.25, IMU bias +/-0.05 rad, IMU noise 0-0.05 rad",
       units_and_conditions="Ranges as listed", locator="Section on robustness (table of randomised parameters)", limitations="Legged robot",
       relevance_to_design="Identify the actuator (voice coil) and latency before randomising", transferability="medium",
       transferability_reason="Different plant", design_implication="EXP-V02 identifies the nose actuator; DR then spans only residual uncertainty",
       search_query="Tan sim-to-real agile locomotion quadruped arXiv 1804.10332", stream="OPT"),
    _r(id="OPT-58", topic="Learned actuator model inside a rigid-body simulator",
       citation="Hwangbo J, Lee J, Dosovitskiy A, Bellicoso D, Tsounis V, Koltun V, Hutter M. Learning agile and dynamic motor skills for legged robots. Science Robotics 4(26):eaau5872 (arXiv 1901.08652)",
       year=2019, doi_or_url="https://arxiv.org/abs/1901.08652", source_type="journal", evidence_class="physical bench experiment",
       access_level="full text", task_or_setup="Actuator network trained on measured data, used in simulation for RL", participants_or_bench="ANYmal robot",
       comparator="Analytical actuator models",
       key_quantitative_findings="Actuator network (MLP on a history of position errors and velocities) learned from data; rigid-body simulation with actuator networks runs about 500,000 time steps per second; policies transferred to the robot",
       units_and_conditions="steps/s", locator="Methods", limitations="Series-elastic actuators", relevance_to_design="Option to learn the voice-coil + flexure response from bench data (EXP-V02)",
       transferability="medium", transferability_reason="Different actuators", design_implication="If the nose's measured response deviates from the physics model, fit a small actuator network and plug it into sim2",
       search_query="Hwangbo learning agile dynamic motor skills legged robots arXiv 1901.08652", stream="OPT"),
    _r(id="EML-70", topic="Review: robot learning from randomised simulations",
       citation="Muratore F, Ramos F, Turk G, Yu W, Gienger M, Peters J. Robot learning from randomized simulations: a review. Frontiers in Robotics and AI (arXiv 2111.00956v2)",
       year=2022, doi_or_url="https://arxiv.org/abs/2111.00956", source_type="review", evidence_class="review", access_level="full text",
       task_or_setup="Review of DR methods", participants_or_bench="n/a", comparator="Static, adaptive, adversarial DR",
       key_quantitative_findings="All simulators are imperfect; DR acts as regularisation; taxonomy static/adaptive/adversarial DR; adaptive DR uses system identification or simulation-based inference with real data; DR cannot guarantee physical plausibility; numerical stability of randomised instances matters",
       units_and_conditions="Qualitative", locator="Sections 2-5", limitations="Review", relevance_to_design="sim2 DR design and its stability checks",
       transferability="high", transferability_reason="Method-level", design_implication="Check each DR sample for numerical stability; move to adaptive DR once EXP-V data exist",
       search_query="Muratore robot learning from randomized simulations review arXiv", stream="EML"),
    _r(id="EML-71", topic="Adaptive DR from real roll-outs (SimOpt)",
       citation="Chebotar Y, Handa A, Makoviychuk V, Macklin M, Issac J, Ratliff N, Fox D. Closing the sim-to-real loop: Adapting simulation randomization with real world experience. IEEE ICRA 2019 (arXiv 1810.05687)",
       year=2019, doi_or_url="https://arxiv.org/abs/1810.05687", source_type="conference", evidence_class="physical bench experiment",
       access_level="full text", task_or_setup="Simulation parameter distribution updated from a few real roll-outs, interleaved with policy training",
       participants_or_bench="Swing-peg-in-hole and drawer opening", comparator="Hand-tuned randomisation",
       key_quantitative_findings="A few real roll-outs suffice to adapt the simulation parameter distribution; policies transferred for swing-peg-in-hole and cabinet-drawer opening",
       units_and_conditions="Task success", locator="Abstract; method", limitations="Manipulation tasks", relevance_to_design="How s2r/ bench data can narrow sim2's DR",
       transferability="medium", transferability_reason="Method-level", design_implication="Use EXP-V bench recordings to update sim2's DR distribution (SimOpt-style)",
       search_query="Chebotar closing the sim-to-real loop arXiv 1810.05687", stream="EML"),
    _r(id="EML-72", topic="Grey-box identification with stochastic differential equations (CTSM)",
       citation="Kristensen NR, Madsen H, Jorgensen SB. Parameter estimation in stochastic grey-box models. Automatica 40(2):225-237",
       year=2004, doi_or_url="https://doi.org/10.1016/j.automatica.2003.10.001", source_type="journal", evidence_class="analytical derivation",
       access_level="full text", task_or_setup="SDE state-space models with discrete measurement noise; EKF-based ML/MAP estimation",
       participants_or_bench="Numerical examples", comparator="An existing estimation tool",
       key_quantitative_findings="ML and MAP estimation over multiple independent data sets with irregular sampling, outliers and missing data (CTSM software); better diffusion-parameter estimates than the compared tool",
       units_and_conditions="Method", locator="Sections 2-4", limitations="EKF linearisation",
       relevance_to_design="Grey-box identification of sim2 parameters (grip, friction, actuator) from bench data", transferability="high",
       transferability_reason="Method-level", design_implication="Identify EXP-V parameters with a stochastic grey-box (process + measurement noise), not least squares on one trace",
       search_query="Kristensen Madsen Jorgensen parameter estimation stochastic grey-box models Automatica pdf", stream="EML"),
]


def _f(x, n=3):
    try:
        return f"{float(x):.{n}g}"
    except Exception:
        return str(x)


def derived(st: Dict) -> List[Dict[str, str]]:
    """Rows for this study's own simulations (numbers from the stage results)."""
    rows = []
    loc = "results/sim2/verification.json; docs/sim_v2.md"
    if st.get("h1check"):
        s = st["h1check"]["splits"]["0.5"]["summary"]
        rows.append(_r(id="CON-66", topic="Simulator v2 reproduces model H1 (Rev H-B) in the linear regime",
                       citation="This ledger's simulation: sim2/h1compare.py, sim2/run_study.py stage h1check (study V, Rev J)", year=2026,
                       doi_or_url="results/sim2/verification.json", source_type="derived simulation", evidence_class="numerical simulation",
                       access_level="full text", task_or_setup="Same scenarios, metrics and tracker as opt/inertial (H1); MuJoCo pen with dynamic nose, refill and grip joints",
                       participants_or_bench="Synthetic writing, test seeds 200-203; 40 cases at r_rot 0.5, 8 each at 0.3 and 0.7", comparator="H1 (opt.inertial.evaluate)",
                       key_quantitative_findings=(f"r_rot 0.5: unmodified ink error within {_f(100 * s['unmod_rel']['max_abs'], 2)} % (tolerance 10 %); "
                                                  f"oracle ratio difference mean {_f(s['oracle']['mean'], 2)}, max {_f(s['oracle']['max_abs'], 2)}, pass {_f(100 * s['oracle']['pass_frac'], 3)} % at +/-0.03; "
                                                  f"causal AKF difference mean {_f(s['akf']['mean'], 2)}, rms {_f(s['akf']['rms'], 2)}, pass {_f(100 * s['akf']['pass_frac'], 3)} % at +/-0.05"),
                       units_and_conditions="Ink error ratio (with correction / without)", locator=loc,
                       limitations="Linear regime; H1 is itself a model; tolerances set by study V", relevance_to_design="sim2 can replace H1 for the Rev J studies",
                       transferability="high", transferability_reason="Code-to-code verification", design_implication="Use sim2 for D, K, N, L; H1 remains the fast reference",
                       search_query="n/a", stream="CON"))
    if st.get("contact"):
        c = st["contact"]
        nb = c["native_block"][0]
        lg = c["lugre"]
        rows.append(_r(id="CON-67", topic="Native MuJoCo contact versus the H1 contact law for a pen on paper",
                       citation="This ledger's simulation: sim2/verify.py (native_block_tests, pen_sliding, lugre_tests)", year=2026,
                       doi_or_url="results/sim2/verification.json", source_type="derived simulation", evidence_class="numerical simulation",
                       access_level="full text", task_or_setup="20 g block tests and the Rev H pen dragged at 20 mm/s",
                       participants_or_bench="MuJoCo 3.6", comparator="Closed forms (CON-58, CON-59) and Coulomb/LuGre analytics",
                       key_quantitative_findings=(f"Native (solref 0.5 ms, solimp 0.99/0.999, impratio 10): static stiffness {_f(nb['static_stiffness_N_per_m']['measured'])} N/m "
                                                  f"(closed form {_f(nb['static_stiffness_N_per_m']['closed_form'])}); creep in stick at half the friction limit "
                                                  f"{_f(nb['creep']['v_creep_m_s'] * 1e6)} um/s (closed form {_f(nb['creep']['closed_form_m_s'] * 1e6)}); "
                                                  f"sliding friction/normal {_f(nb['sliding_mu_elliptic'])} (mu 0.12); H1 law: pre-sliding stiffness "
                                                  f"{_f(lg['presliding_stiffness_N_per_m']['measured'])} N/m (closed form {_f(lg['presliding_stiffness_N_per_m']['closed_form'])}); "
                                                  f"stick-slip period {_f(lg['stick_slip']['period_s'])} s versus Coulomb {_f(lg['stick_slip']['period_analytic_s'])} s"),
                       units_and_conditions="N/m, um/s, s", locator=loc, limitations="Friction parameters are ASSUMPTION until EXP-Q01/V01",
                       relevance_to_design="Default contact law for ink studies", transferability="high", transferability_reason="Engine-level verification",
                       design_implication="H1 law for micrometre ink metrics; native contacts only for coarse RL and plug-ins", search_query="n/a", stream="CON"))
    if st.get("convergence") or st.get("energy") or st.get("gyro"):
        parts = []
        cv = st.get("convergence") or {}
        if "h1_contact" in cv:
            rr = cv["h1_contact"]["rows"]
            parts.append("ink path difference vs 12.5 us: " + ", ".join(f"{_f(r['dt_us'])} us {_f(r['ink_path_diff_um'])} um" for r in rr[1:]))
            parts.append("oracle ratio " + "/".join(_f(r["oracle_ratio"], 4) for r in rr))
        if st.get("energy"):
            mx = max(abs(r["residual_rel"]) for r in st["energy"]["rows"])
            parts.append(f"energy balance residual <= {_f(mx, 2)} of the energy scale (conservative, damped, actuated; four integrators)")
        if st.get("gyro"):
            parts.append(f"rotor reaction torque vs h x omega max relative error {_f(st['gyro']['max_rel_error'], 2)}")
        rows.append(_r(id="CON-68", topic="Simulator v2 calculation verification: time step, energy, gyroscopic torque",
                       citation="This ledger's simulation: sim2/verify.py (convergence, energy_audit, gyro_torque)", year=2026,
                       doi_or_url="results/sim2/verification.json", source_type="derived simulation", evidence_class="numerical simulation",
                       access_level="full text", task_or_setup="Rev H case seed 300, 8 Hz 1 mm; pen in the air; rotor on a driven gimbal",
                       participants_or_bench="MuJoCo 3.6", comparator="Finest step; work-energy balance; analytic h x omega",
                       key_quantitative_findings="; ".join(parts), units_and_conditions="um, relative", locator=loc,
                       limitations="Single case for convergence", relevance_to_design="Time step 25 us and implicitfast are adequate",
                       transferability="high", transferability_reason="Code verification", design_implication="Keep 25 us for ink studies; 50 us for RL if the ink metric tolerance allows",
                       search_query="n/a", stream="CON"))
    if st.get("validate"):
        v = st["validate"]
        w = v.get("writer_lognormal", {})
        g = v.get("writer_glyph", {})
        txt = (f"sigma-lognormal writer: mean speed {_f(w['speed_mm_s']['mean'])} mm/s, stroke median {_f(w['stroke_duration_ms']['median'])} ms, "
               f"velocity energy 50/90/95 % by {_f(w['velocity_spectrum']['f50_Hz'])}/{_f(w['velocity_spectrum']['f90_Hz'])}/{_f(w['velocity_spectrum']['f95_Hz'])} Hz, "
               f"power-law exponent {_f(w['power_law_beta']['mean'])}")
        if "speed_mm_s" in g:
            txt += (f"; glyph writer: {_f(g['speed_mm_s']['mean'])} mm/s, strokes {_f(g['stroke_duration_ms']['median'])} ms, "
                    f"50/90 % by {_f(g['velocity_spectrum']['f50_Hz'])}/{_f(g['velocity_spectrum']['f90_Hz'])} Hz, exponent {_f(g['power_law_beta']['mean'])}")
        txt += "; comparators CON-20 (phrase 30.5 mm/s), CON-24 (strokes 90-150 ms), CON-25 (50/90/95 % by 3.1/4.9/5.9 Hz), CON-27 (exponent 2/3)"
        rows.append(_r(id="CON-69", topic="Synthetic writers of the simulators against measured writing kinematics",
                       citation="This ledger's calculation: sim2/validate.py writer_kinematics (study V)", year=2026,
                       doi_or_url="results/sim2/validation.json", source_type="derived calculation", evidence_class="calculation",
                       access_level="full text", task_or_setup="Intended pen paths of stabpen.signals (sigma-lognormal) and fusion.data glyph writer, training seeds",
                       participants_or_bench="Synthetic writers", comparator="CON-20, CON-24, CON-25, CON-27",
                       key_quantitative_findings=txt, units_and_conditions="mm/s, ms, Hz, exponent", locator="results/sim2/validation.json",
                       limitations="Intended paths only; the comparators are other populations and tasks", relevance_to_design="Whether tremor-band writing content is realistic",
                       transferability="medium", transferability_reason="Synthetic versus measured writing",
                       design_implication="Calibrate the writers to recorded pen kinematics (EXP-V05) before trusting 3-15 Hz metrics", search_query="n/a", stream="CON"))
    if st.get("myo"):
        tab = st["myo"].get("table", [])
        z8 = [t for t in tab if t["f_Hz"] == 8.0]
        rng = {ax: (min(t["Z_myoarm_N_per_m"] for t in z8 if t["axis"] == ax), max(t["Z_myoarm_N_per_m"] for t in z8 if t["axis"] == ax),
                    [t["Z_hap26_N_per_m"] for t in z8 if t["axis"] == ax][0]) for ax in "xyz"} if z8 else {}
        un = [(r["cocontraction"], r["n_unstable"], r["max_growth_per_s"]) for r in st["myo"]["rows"]]
        rows.append(_r(id="HAP-102", topic="MyoArm pen-point impedance over co-contraction (Hill-type muscles)",
                       citation="This ledger's simulation: sim2/myo.py (MyoSuite 2.12.2 MyoArm, linearised about a pen grasp)", year=2026,
                       doi_or_url="results/sim2/myo_impedance.json", source_type="derived simulation", evidence_class="numerical simulation",
                       access_level="full text", task_or_setup="MyoArm with a 5 g pen welded to three distal phalanges; uniform activation 0-0.3; gravity off",
                       participants_or_bench="MyoSuite MyoArm (38 joints, 63 muscles)", comparator="HAP-26 nominal tip impedance, H1",
                       key_quantitative_findings=("|Z| at 8 Hz over c 0-0.3: " + "; ".join(f"{ax} {_f(v[0])}-{_f(v[1])} N/m (HAP-26 {_f(v[2])})" for ax, v in rng.items())
                                                  + "; divergent modes (count, growth 1/s) per level: " + ", ".join(f"c {c:g}: {n} ({_f(g_, 2)})" for c, n, g_ in un)),
                       units_and_conditions="N/m at 8 Hz; 1/s", locator="results/sim2/myo_impedance.json",
                       limitations="No short-range stiffness (HAP-101), no reflexes, rigid pad welds, model joint damping",
                       relevance_to_design="Scaling of DR ranges with co-contraction", transferability="low",
                       transferability_reason="Generic musculoskeletal model with known stiffness deficits",
                       design_implication="Widen b_arm DR upward; measure pen-grasp impedance (EXP-V04)", search_query="n/a", stream="HAP"))
    if st.get("arm"):
        a = st["arm"]
        rr = a.get("arm_vs_h1", [])
        txt = f"arm tip impedance fitted to H1 (rms relative error {_f(a['calibration']['rms_rel_error'], 2)}); " + "; ".join(
            f"seed {r['seed']} {r['f0']:g} Hz: oracle ratio arm {_f(r['arm']['oracle']['ratio'])} vs H1 hand {_f(r['h1']['oracle_ratio'])}" for r in rr)
        rows.append(_r(id="HAP-103", topic="Articulated arm hand model versus H1's lumped hand",
                       citation="This ledger's simulation: sim2/hand.py, sim2/validate.py arm_case (study V)", year=2026,
                       doi_or_url="results/sim2/validation.json", source_type="derived simulation", evidence_class="numerical simulation",
                       access_level="full text", task_or_setup="Forearm-wrist-hand chain with tremor torques, writer controller; Rev H nose (oracle)",
                       participants_or_bench="Synthetic writing, training seeds 300-301", comparator="H1 hand in sim2",
                       key_quantitative_findings=txt, units_and_conditions="ratio", locator="results/sim2/validation.json",
                       limitations="Arm impedance fitted, not measured", relevance_to_design="Hand-model sensitivity of device performance",
                       transferability="medium", transferability_reason="Model-to-model", design_implication="Report device results for both hand models",
                       search_query="n/a", stream="HAP"))
    if st.get("validate") and st["validate"].get("tremor_spectra"):
        ts = st["validate"]["tremor_spectra"]
        wr = st["validate"].get("wrist_resonance", {})
        txt = "; ".join(f"{r['kind']} {r['f0']:g} Hz: ink band rms {_f(r['ink']['rms_um'])} um, peak {_f(r['ink']['peak_Hz'])} Hz" for r in ts)
        if wr:
            txt += f"; pen-tip response to wrist torque peaks at {_f(wr['nominal']['peak_Hz'])} Hz (+300 g: {_f(wr['loaded']['peak_Hz'])} Hz)"
            if "f_n_wrist_Hz" in wr["nominal"]:
                txt += (f"; fitted wrist flexion natural frequency {_f(wr['nominal']['f_n_wrist_Hz'])} Hz, +300 g "
                        f"{_f(wr['loaded']['f_n_wrist_Hz'])} Hz (CALC), damping ratio {_f(wr['nominal']['zeta_wrist'], 2)}")
        rows.append(_r(id="PDT-58", topic="Tremor profiles through the arm model (spectra, gating, loading)",
                       citation="This ledger's simulation: sim2/tremor.py, sim2/validate.py (study V)", year=2026,
                       doi_or_url="results/sim2/validation.json", source_type="derived simulation", evidence_class="numerical simulation",
                       access_level="full text", task_or_setup="ET, PD action, PD rest (gated) and physiological profiles as forearm/wrist torques",
                       participants_or_bench="Synthetic writing seed 300", comparator="PDT-55, PDT-56 (bands, loading)",
                       key_quantitative_findings=txt, units_and_conditions="um, Hz", locator="results/sim2/validation.json",
                       limitations="Tremor inputs are parametric (by construction); only the mechanical filtering is tested",
                       relevance_to_design="Tremor inputs for D, K, N, L", transferability="medium", transferability_reason="Model",
                       design_implication="Calibrate torque amplitudes per subject from pen recordings (EXP-V03)", search_query="n/a", stream="PDT"))
    if st.get("sensors"):
        s = st["sensors"]
        raw = s["imu"]["raw_reading"]["acc_nd_ug_per_rtHz_x_y"]
        rows.append(_r(id="OPT-59", topic="Simulator v2 sensor models against fusion/ and MuJoCo's accelerometer",
                       citation="This ledger's simulation: sim2/sensors.py, sim2/verify.py sensor_tests (study V)", year=2026,
                       doi_or_url="results/sim2/verification.json", source_type="derived simulation", evidence_class="numerical simulation",
                       access_level="full text", task_or_setup="Pen held still (noise) and an 8 Hz tremor run (kinematic consistency)",
                       participants_or_bench="MuJoCo 3.6 + fusion.sensors (LSM6DSV16X class, OPT-37)", comparator="fusion.sensors settings",
                       key_quantitative_findings=(f"accelerometer noise density {_f(raw[0])}/{_f(raw[1])} ug/rtHz (fusion setting {_f(s['imu']['acc_nd_fusion_ug_per_rtHz'])}), "
                                                  f"ODR {_f(s['imu']['raw_reading']['odr_Hz'])} Hz; native accelerometer vs velocity differentiation corr "
                                                  f"{_f(s['accelerometer_consistency_3_15Hz']['corr_native_vs_velocity_diff'], 4)}; page latency {_f(s['page']['latency_s'] * 1e3)} ms at {_f(s['page']['rate_Hz'])} Hz"),
                       units_and_conditions="ug/rtHz, Hz, ms", locator="results/sim2/verification.json", limitations="Models only; no hardware",
                       relevance_to_design="The Gym environment's observations", transferability="medium", transferability_reason="Datasheet-level models",
                       design_implication="Measure the assembled pen's sensor noise and latency (EXP-V02)", search_query="n/a", stream="OPT"))
    if st.get("env"):
        e = st["env"]
        sp = e["speed"][0]
        rows.append(_r(id="EML-73", topic="Gymnasium environment of simulator v2: speed and randomisation",
                       citation="This ledger's simulation: sim2/env.py (study V)", year=2026, doi_or_url="results/sim2/env_benchmark.json",
                       source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
                       task_or_setup="Pen's own sensors in, nose (and plug-in) commands out; 25 DR factors", participants_or_bench="One core of a shared 4-core machine",
                       comparator="Real time",
                       key_quantitative_findings=f"{_f(sp['env_steps_per_s'])} env steps/s at {_f(sp['control_hz'])} Hz control ({_f(sp['sim_seconds_per_wall_second'])} simulated s per wall s) with the H1 contact law; obs {sp['obs_dim']}, act {sp['act_dim']}",
                       units_and_conditions="steps/s under load from other studies", locator="results/sim2/env_benchmark.json",
                       limitations="Speed measured under shared load", relevance_to_design="Budget for RL training (study L)", transferability="high",
                       transferability_reason="Same code", design_implication="Train with parallel workers or the 50 us step; keep the 25 us H1 law for evaluation",
                       search_query="n/a", stream="EML"))
    return rows


def rows(st: Dict) -> List[Dict[str, str]]:
    der = derived(st)
    for r in der:
        r["retrieved"] = "2026-09-29"          # date of this study's runs
    return PRIMARY + der
