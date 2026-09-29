"""Design values of the paper-grounded heel drive, each with a label and a source.

Labels: CALC (calculated here), SIM (simulated here), MFR (manufacturer statement, ledger id), LIT (literature, ledger
id), ASSUMPTION (chosen here; docs/grounded_drive.md names the experiment EXP-D.. that measures it).  Nothing here is a
measurement of our hardware.  Proposed ledger ids are those of results/drive/evidence_rows.csv (HAP-60..., AMF-100...,
CON-36..., PAT-30...); existing ids are in docs/evidence.csv.

Frames: pen frame z along the axis from the ball tip, x in the tilt plane positive away from the paper, y lateral
(results/revH/layout.json).  Page frame: the HW1 page plane (x right, y up the page).
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class V:
    value: object
    unit: str
    label: str
    source: str
    note: str = ""

    def as_dict(self):
        d = {"value": self.value, "unit": self.unit, "label": self.label, "source": self.source}
        if self.note:
            d["note"] = self.note
        return d


# ----------------------------------------------------------------------------- writing force (normal load)
WRITING = {
    "N_mean": V(1.01, "N", "LIT", "CON-01 (Schomaker & Plamondon 1990: mean of 16 subject means 1.01 N)"),
    "N_between_sd": V(0.43, "N", "LIT", "CON-01 between-subject SD 0.43 N; subject means 0.56-2.08 N"),
    "N_min_writer": V(0.45, "N", "ASSUMPTION", "clip of the per-writer mean below CON-01's lowest subject mean 0.56 N",
                      "children with handwriting difficulty 0.77 +/- 0.36 N (CON-04)"),
    "N_max_writer": V(2.2, "N", "ASSUMPTION", "clip above CON-01's highest subject mean 2.08 N"),
    "N_within_sd": V(0.18, "N", "LIT", "CON-01 within-word SD 0.11-0.25 N, mean 0.18 N"),
    "N_fluct_hz": V(1.5, "Hz", "LIT", "CON-04: 1.3-1.6 force fluctuations per second (digit forces)",
                    "used as the corner of the band-limited within-word variation (ASSUMPTION transfer to tip force)"),
    "N_floor": V(0.15, "N", "ASSUMPTION", "lowest instantaneous writing force while the pen is down"),
    "F_c_refill": V(0.15, "N", "ASSUMPTION", "Rev H refill constant-force spring (HW1 Pen.F_c; pencil study)"),
    "theta_deg": V(50.0, "deg", "LIT", "CON-02 pen angle about 50 deg (HW1 Writing.theta_deg)"),
    "theta_range_deg": V((35.0, 75.0), "deg", "ASSUMPTION", "REQ-RVH-002 writing tilts (front_end.py rules)"),
}

# ----------------------------------------------------------------------------- friction and contact of the drive element
CONTACT = {
    "mu_drive_range": V((0.6, 1.2), "-", "ASSUMPTION",
                        "elastomer tyre on paper; paper-feed rollers (polyurethane, JIS-A 43-75) measure 1.30-2.20 new and "
                        "1.05-1.52 after 300 000 sheets on PPC paper (AMF-111); a general-purpose tyre on mixed papers, "
                        "with paper dust and ink, is taken lower", "EXP-D01 measures it on 6 papers"),
    "mu_hat_init": V(0.6, "-", "ASSUMPTION", "the controller's starting traction estimate (lower end of the range)"),
    "mu_static_ratio": V(1.1, "-", "ASSUMPTION", "static/kinetic for the rubber tyre (rubber has little stick-slip gap)"),
    "k_lat": V(1500.0, "N/m", "CALC", "tyre tangential stiffness: Mindlin 8aG/(2-nu) in series with O-ring shear G A/h "
               "(contact.tyre_stiffness; G, a, A, h ASSUMPTION)", "range 700-3000 N/m; EXP-D02"),
    "v_stribeck": V(0.002, "m/s", "ASSUMPTION", "HW1 Writing.v_s"),
    "tan_delta": V(0.12, "-", "ASSUMPTION", "polyurethane / NBR tyre loss factor at 10-100 Hz (typical range 0.05-0.3)"),
    "E_tyre": V(8.0e6, "Pa", "ASSUMPTION", "tyre Young's modulus (Shore A about 75-80)"),
    "mu_skid": V(0.12, "-", "ASSUMPTION", "HW1 Writing.mu_skid (PTFE-coated POM skid on paper)"),
    "mu_paper_desk": V((0.25, 0.5), "-", "ASSUMPTION",
                       "paper on a desk; paper-to-paper COF methods have 12-13 % repeatability and 24-27 % "
                       "reproducibility between labs (AMF-113), so any value must be measured", "EXP-D03"),
}

# ----------------------------------------------------------------------------- hand (HAP-26, as HW1 and the board)
HAND_CASES = {
    "relaxed": {"k_arm": 170.0, "b_arm": 11.0, "label": "LIT HAP-26 nominal (config hand.*)"},
    "lightly_resisting": {"k_arm": 533.0, "b_arm": 27.6, "label": "LIT HAP-26 upper 95 % CI arm (ASSUMPTION: co-contraction)"},
}
RELAX_TAU_S = V(0.25, "s", "ASSUMPTION", "board/control.py lead-through: the relaxed writer's anchor follows the hand")

# ----------------------------------------------------------------------------- control and safety
CONTROL = {
    "tick_hz": V(2000.0, "Hz", "ASSUMPTION", "as the Rev H controller (HW1 Pen.tick_hz)"),
    "F_cap": V(0.5, "N", "ASSUMPTION",
               "software cap on the heel force; handwriting-guidance devices used 0.43-0.49 N (LIT HAP-15, HAP-16, HAP-51), "
               "the board 0.4 N; ISO/TS 15066 hand limit is 140 N quasi-static (LIT HAP-70)", "EXP-D07"),
    "k_safe": V(0.8, "-", "ASSUMPTION", "command at most 0.8 x the estimated traction mu_hat x N_d (slip margin)"),
    "mu_hat0": V(0.8, "-", "ASSUMPTION", "the controller's starting traction estimate; it does not know the paper "
                 "(test cases draw the true mu from 0.6-1.2); the slip rule lowers it", "EXP-D01"),
    "slew_N_s": V(20.0, "N/s", "ASSUMPTION", "force rate limit (the board uses 8 N/s at 25 Hz; the heel motor is faster)"),
    "yield_err_mm": V(4.0, "mm", "ASSUMPTION", "board rule (docs/guidance_board.md 5.4)"),
    "yield_time_s": V(0.3, "s", "ASSUMPTION", "board rule; LIT HAP-22/23 advise yielding to a persistent writer"),
    "slip_rule": V("travel > 1.5 x 1.2 N_d / k_lat + 8 mm/s x 4 ms", "m", "ASSUMPTION",
                   "slip flag: the heel's travel over the element surface (optical sensor minus element odometry, "
                   "integrated with a 50 ms leak) exceeds what the tyre can deflect elastically; on each new flag "
                   "mu_hat drops by 10 % (floor 0.3), and it recovers toward its start over about 2 s without slip",
                   "EXP-D05"),
    "slip_v_mm_s": V(8.0, "mm/s", "ASSUMPTION", "sensor-noise margin of the slip rule (x 4 ms)"),
    "slip_t_s": V(0.05, "s", "ASSUMPTION", "leak time of the relative-travel integrator"),
    "k_fc": V(0.7, "-", "ASSUMPTION", "share of the modelled rolling resistance and reflected-inertia force that the "
              "drive compensates (feed-forward); 1.0 would be perfect knowledge"),
    "steer_law": V("pure pursuit or Stanley (chosen in tuning)", "-", "ASSUMPTION",
                   "steered wheel path laws: pure pursuit on a look-ahead point, or Stanley (tangent L_t ahead plus "
                   "atan(k e / v)); results/drive/rules.json records which one the tuning chose"),
    "N_sense_noise": V(0.01, "N", "ASSUMPTION", "normal-load sensing noise (Hall on the preload spring, OPT-45 class)"),
    "F_lat_noise": V(0.005, "N", "ASSUMPTION", "lateral-force sensing noise (Hall on the wheel mount deflection)"),
    "page_sensor": V((1000.0, 2e-3, 3e-6), "Hz, s, m", "ASSUMPTION", "HW1 page sensor (rate, latency, noise)"),
    "motor_tau_s": V(0.0005, "s", "CALC", "current-loop time constant: L/R of the 6 mm motors 0.004-0.02 ms plus the "
                     "2 kHz tick (AMF-100, AMF-101); the tick dominates"),
}

# ----------------------------------------------------------------------------- board (for the comparison runs)
BOARD_REF = V(0.4, "N", "SIM/CALC", "docs/guidance_board.md: cap 0.4 N, 25 Hz, 8 ms; +1 N normal pull")


def table(d: dict) -> dict:
    return {k: v.as_dict() for k, v in d.items()}


def all_tables() -> dict:
    return {"writing": table(WRITING), "contact": table(CONTACT), "control": table(CONTROL),
            "hand_cases": HAND_CASES, "relax_tau_s": RELAX_TAU_S.as_dict(), "board_ref": BOARD_REF.as_dict()}


def ball_normal(theta_deg: float = 50.0, F_c: float = 0.15) -> float:
    """Normal force on the ink ball (N): the refill's constant-force spring along the axis (HW1 Pen.ball_normal)."""
    return F_c / math.sin(math.radians(theta_deg))
