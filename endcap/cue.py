r"""Guidance by feel: what the literature supports for pseudo-force and torque cues, applied to the Rev H pen.

A pseudo-force (asymmetric vibration) is a PERCEPTUAL cue: its time-averaged force is zero, so it cannot move the pen or
the hand; people may feel a pull and may move with it.  A CMG torque pulse is a real torque, but it is lent, not given:
the gimbal must swing back, so the net angular impulse over a pulse-and-reset cycle is zero.
This module computes (CALC unless stated):
  * the acceleration a cue actuator produces at the finger-pad zone of the Rev H pen held in the HAP-26 hand (linear
    model), and the force needed to reach the acceleration levels used in the psychophysics (LIT HAP-80, HAP-85);
  * the share of handwriting motion slow enough to follow a cue with a human response delay (0.33 s for fast responders,
    LIT HAP-84), on the synthetic writers (SIM);
  * a table of cue channels with direction accuracy, strength, delay and caveats, from the ledger rows.
Evidence status: CALCULATION + LITERATURE (+ SIMULATION for the writing spectrum).  No person was tested.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import torch

from . import linear_torch as LT
from . import params as P


def grip_accel_per_N(f, r_rot=0.5, z_force=P.Z_CAP, z_grip=0.032):
    """Acceleration amplitude (m/s2) of the finger-pad point per 1 N sinusoidal force applied to the pen at the end-cap,
    transverse (t1 and t2 directions); linear model with the HAP-26 hand (CALC)."""
    el = LT.EndcapLinear(r_rot)
    M, D, K, n = el.matrices({})
    w = 2 * math.pi * f
    out = []
    Jg = torch.tensor(LT.point_jac8(el.lm, z_grip))
    Jf = torch.tensor(LT.point_jac8(el.lm, z_force))
    for t in (el.t1, el.t2):
        F = (Jf.T @ torch.tensor(t)).to(torch.complex128)
        X = el.solve(M, D, K, w, F)
        a = (w * w) * torch.linalg.norm(torch.abs(Jg.to(torch.complex128) @ X))
        out.append(float(a))
    return out


def force_for_levels(f_list=(40.0, 75.0), levels=(8.0, 40.0, 60.0), splits=P.SPLITS):
    rows = []
    for f in f_list:
        for rr in splits:
            a1, a2 = grip_accel_per_N(f, rr)
            a = min(a1, a2)
            rows.append({"f_Hz": f, "r_rot": rr, "grip_acc_per_N_t1": a1, "grip_acc_per_N_t2": a2,
                         **{f"F_for_{lv:g}_m_s2_N": lv / a for lv in levels}})
    return rows


def writing_share_slower_than(latency_s=0.33, seeds=(300, 301, 302, 303)):
    """Share of the synthetic writers' intended-path power (above 0.3 Hz) below f_c = 1 / (2 x latency): the part of the
    motion a cue-and-respond loop could follow (SIM on sim/pensim writers; CALC)."""
    from scipy import signal as sps
    from opt.inertial import scen as SC
    fc = 1.0 / (2.0 * latency_s)
    shares = []
    for s in seeds:
        sc = SC.get(s)
        t = sc.t
        fs = 1.0 / (t[1] - t[0])
        dec = 50
        x = sc.intended[::dec]
        fsd = fs / dec
        xh = sps.sosfiltfilt(sps.butter(2, 0.3, btype="high", fs=fsd, output="sos"), x, axis=0)
        fr, Pw = sps.welch(xh, fs=fsd, nperseg=int(2 * fsd), axis=0)
        Pt = Pw.sum(axis=1)
        shares.append(float(Pt[fr <= fc].sum() / Pt.sum()))
    return {"latency_s": latency_s, "f_follow_Hz": fc, "share_mean": float(np.mean(shares)), "shares": shares}


def channel_table(pen_mass_g=120.0, cmg=None) -> List[Dict]:
    """Cue channels for 'guide by feel' (LIT with ledger ids; pen-specific notes are CALC or ASSUMPTION).  `cmg` is the
    optimised CMG design summary (endcap/optimise.summarize), used for the pen-scale torque, spin power and tone."""
    L = P.CUE_LIT
    if cmg is not None:
        k = {"SP2": 2.0, "SP1": 2.0, "DG1": 1.0, "DG2": 2.0, "PL2": 1.0}.get(cmg["class"], 1.0)
        tau3 = k * cmg["H"] * min(P.GIMBAL_DRIVE["rate_max"], 2 * math.pi * 3.0 * cmg["x"]["delta"]) * 1e3
        cmg_strength = f"51 mN m in HAP-82; the optimised 45 g end-cap CMG ({cmg['class']}) reaches {tau3:.0f} mN m at 3 Hz (CALC)"
        cmg_cost = (f"the whole end-cap ({cmg['mass_g']:.0f} g), {cmg['P_spin_W']:.2f} W spin power, spin-up "
                    f"{cmg['extras']['spin_up_s']:.0f} s, a {cmg['extras']['tone_Hz']:.0f} Hz tone (CALC)")
    else:
        cmg_strength = "51 mN m in HAP-82"
        cmg_cost = "the whole end-cap, spin power, spin-up time, a rotor tone"
    return [
        {"channel": "Asymmetric vibration (pseudo-force), handle-held voice-coil vibrators",
         "what_it_is": "perceptual pull; zero mean force",
         "direction_accuracy": f"median {L['tanabe2024_dir_correct'][0] * 100:.1f} % (healthy, 75 Hz, 60 m/s2; HAP-85); about 90 % "
                               "at 10 Hz for a DC-motor rotor (HAP-86)",
         "strength": f"felt like {L['traxion_equiv_force_N'][0]:.2f} N (s.d. {L['traxion_equiv_force_N'][1]:.2f} N) for a 5.2 g actuator "
                     "(HAP-81); Tanabe's handles moved at 8-60 m/s2 (HAP-80, HAP-85)",
         "effect_on_movement": "congruent cue raised peak wrist velocity, Cohen d 0.22 (HAP-85); agency fell",
         "people_with_tremor": "near chance on sides with tremor or hemiplegia in many participants (PDT-39, preprint)",
         "cost_in_pen": "5-11 g actuator (HAP-86, AMF-124); or the reaction mass itself; power 0.1-1 W while on (CALC)",
         "caveats": "shakes the ink (see SIM cue cases); the actuators 'must be attached very precisely' to the hand (HAP-84, "
                    "related-work remark); psychophysics protocols pause for 'fatigue ... and the adaptation to the stimulus' (HAP-85)"},
        {"channel": "CMG torque pulse (real, lent torque)",
         "what_it_is": "real torque for 0.1-0.2 s, then a slower opposite reset",
         "direction_accuracy": f"{L['walker2018_dir_correct'][0] * 100:.1f} % (12 healthy; 51 mN m pulses, 198 g device; HAP-82)",
         "strength": cmg_strength,
         "effect_on_movement": "orientation guidance succeeded in 60/60 trials but slowly: median 8.6 s, path 3.3x direct (HAP-82)",
         "people_with_tremor": "not tested in the literature found",
         "cost_in_pen": cmg_cost,
         "caveats": "the torque must be paid back (reset); gyroscopic side effects when the pen is turned (uncancelled H)"},
        {"channel": "Skin stretch at the finger pads (holdable device)",
         "what_it_is": "tangential displacement of the pads, 3 mm over 0.2 s",
         "direction_accuracy": f"> {L['walker2019_dir_correct'][0] * 100:.1f} % for 8 directions (20 healthy; HAP-84)",
         "strength": "3 mm pad displacement; reaction goes into the palm (HAP-84)",
         "effect_on_movement": "people moved in the cued direction before training; delay 0.33 s (fast) or 1.56 s (slow) (HAP-84)",
         "people_with_tremor": "not tested",
         "cost_in_pen": "would need moving pads in the grip sleeve, not an end-cap (out of this study's scope)",
         "caveats": "suggests the grip, not the end-cap, is the better place for guidance by feel"},
        {"channel": "Plain vibration buzz (existing Rev H LRA)",
         "what_it_is": "a symbolic alert, no direction",
         "direction_accuracy": "none (needs a learned code)",
         "strength": "coin LRA about 1 G class (AMF-45)",
         "effect_on_movement": "PD 'write bigger' cues work as symbolic reminders (PDT-18, PDT-19)",
         "people_with_tremor": "usable",
         "cost_in_pen": "1 g, already in Rev H",
         "caveats": "no direction"},
    ]
