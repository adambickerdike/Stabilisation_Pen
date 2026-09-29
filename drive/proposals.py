"""Study D's proposals for the lead: requirement rows (docs/requirements.csv columns) and bench/human experiments.

Nothing here is a result.  Every threshold is a hypothesis to test (ASSUMPTION unless labelled), written so that an
experiment can pass or fail it.  The report stage writes results/drive/requirements_rows.csv and
results/drive/experiments.json; docs/grounded_drive.md shows the same tables.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

REQ_HEADER = ["id", "area", "title", "requirement", "rationale", "source", "verification", "evidence_status",
              "current_estimate", "trace", "status"]

REQUIREMENTS: List[Dict] = [
    dict(id="REQ-DRV-001", area="drive", title="Heel force cap",
         requirement="The heel drive's force on the pen stays at or below 0.5 N (software cap) and at or below 0.8 x the "
                     "estimated traction (mu_hat x wheel load); the physical limit is mu x preload (about 0.33-0.66 N)",
         rationale="Handwriting-guidance devices used 0.43-0.49 N; the desk board 0.4 N; far below ISO/TS 15066 hand limits",
         source="HAP-15; HAP-16; HAP-51; HAP-70; docs/grounded_drive.md s4",
         verification="EXP-D07", evidence_status="CALC; SIM", current_estimate="cap met in all SIM runs (force p95 and max in s5)",
         trace="drive/plant.py supervisor", status="proposed"),
    dict(id="REQ-DRV-002", area="drive", title="The writer always wins",
         requirement="The drive yields (force to zero within 0.1 s) when the pen is held more than 4 mm off the "
                     "template for 0.3 s, when the writer's grip force against the drive exceeds 0.5 N for 0.3 s, or "
                     "on lift; it never keeps pushing against a stalled pen",
         rationale="Users resent tools that act against their intention; a writer set on 'b' must still write 'b'",
         source="HAP-22; HAP-23; HAP-62; SIM reversal (writer set on b: 0 % converted)",
         verification="EXP-D07; EXP-D08", evidence_status="SIM", current_estimate="see s5 (c)", trace="drive/plant.py",
         status="proposed"),
    dict(id="REQ-DRV-003", area="drive", title="Passive by default",
         requirement="In guidance and tremor modes the wheel is steered (and braked) only: it cannot move the pen on "
                     "its own. The wheel is driven only in an explicit lead-through or autowrite mode the user turns "
                     "on, and never starts a stroke",
         rationale="Cobot principle: steering channels the writer's own motion with almost no power (intrinsically "
                   "passive); Rev J envelope: 'writes for you' only in an explicit mode",
         source="HAP-60; docs/revJ_plan.md s6", verification="design review; EXP-D08", evidence_status="PROPOSED DESIGN",
         current_estimate="met by the mode logic (SIM)", trace="drive/scenarios.py drive_for", status="proposed"),
    dict(id="REQ-DRV-004", area="drive", title="Traction on paper",
         requirement="Tyre-paper kinetic friction >= 0.6 on the six reference papers at 0.3-0.6 N, dry and at 60 % RH; "
                     "preload 0.55 N +/- 10 %",
         rationale="The usable force is mu x wheel load; rubber on paper is 1.05-2.2 for feed rollers, but paper "
                   "friction tests reproduce only within 24-27 % between labs",
         source="AMF-111; AMF-113", verification="EXP-D01", evidence_status="LIT; ASSUMPTION",
         current_estimate="design range 0.6-1.2 (ASSUMPTION)", trace="drive/params.py CONTACT", status="proposed"),
    dict(id="REQ-DRV-005", area="drive", title="Slip detection",
         requirement="Gross wheel slip is detected within 50 ms (paper sensor against wheel odometry) and the command "
                     "is lowered; false slip flags fewer than 1 per 10 s of writing",
         rationale="Slip wastes force and marks the paper; the SIM detector raises many false flags at mode switches",
         source="AMF-109; SIM (slip flags against true sliding)", verification="EXP-D05", evidence_status="SIM; ASSUMPTION",
         current_estimate="true sliding < 1 % of contact time; detector flags much more often (s5)",
         trace="drive/plant.py slip rule", status="proposed"),
    dict(id="REQ-DRV-006", area="drive", title="Steering speed",
         requirement="Steering servo bandwidth >= 40 Hz and rate >= 300 rad/s at the wheel",
         rationale="Letter headings turn at up to 71 rad/s (p90) and 283 rad/s (p99) on the synthetic writers",
         source="CON-37; CALC drive/concepts.heading_rates", verification="EXP-D04 (bench)", evidence_status="CALC",
         current_estimate="0620 B + crown 2:1: about 1570 rad/s no-load at 3.7 V (CALC); SIM servo limited to 500 rad/s", trace="drive/concepts.py",
         status="proposed"),
    dict(id="REQ-DRV-007", area="drive", title="Roll and tilt tolerance",
         requirement="The wheel keeps contact over tilts 35-75 deg and pen roll +/-20 deg (spring travel >= 0.54 mm)",
         rationale="Writers roll the pen; the wheel sits at one azimuth of the heel",
         source="CALC drive/geometry.py", verification="EXP-D04", evidence_status="CALC",
         current_estimate="0.54 mm travel gives 20 deg (CALC)", trace="drive/run_study.chosen_heel", status="proposed"),
    dict(id="REQ-DRV-008", area="drive", title="Front-end size and ink view",
         requirement="Heel contact radius <= 9.0 mm; front sleeve <= 18.5 mm at the heel and <= 24 mm where held; "
                     "the heel stays open 120 deg on top so the ink stays visible",
         rationale="The drive must sit outside the swinging nose; the Rev J envelope allows 24 mm where held",
         source="CALC drive/geometry.py; docs/revJ_plan.md s6", verification="CAD review; EXP-D04",
         evidence_status="CALC; PROPOSED DESIGN", current_estimate="8.75 mm; 18.3 mm", trace="mechanics/cad/heel_drive.py",
         status="proposed"),
    dict(id="REQ-DRV-009", area="drive", title="Power and heat",
         requirement="Heel drive electrical power (motors, drivers, paper sensor) <= 0.15 W mean in any mode; winding "
                     "rise < 10 K; the pen still writes >= 8 h with assistance on",
         rationale="Rev H uses about 0.08 W; the 750 mAh cell must last a school day",
         source="AMF-100; AMF-109; docs/revH_concept.md", verification="EXP-D06", evidence_status="CALC; SIM",
         current_estimate="see s4.5", trace="drive/scenarios.drive_metrics", status="proposed"),
    dict(id="REQ-DRV-010", area="drive", title="Noise",
         requirement="Drive noise <= 35 dB(A) at 30 cm while guiding (ASSUMPTION threshold, quiet classroom)",
         rationale="Two 6 mm motors and watch-scale gears may whine", source="ASSUMPTION", verification="EXP-D06",
         evidence_status="ASSUMPTION", current_estimate="unknown", trace="", status="proposed"),
    dict(id="REQ-DRV-011", area="drive", title="Paper must be held",
         requirement="Instructions and app state that the sheet must be held (other hand, clip or pad) whenever the "
                     "drive pushes; the drive's force stays below the sheet's holding force",
         rationale="A loose sheet slides when the drive's reaction exceeds mu_paper-desk x the loads on it",
         source="CALC drive/contact.paper_hold; AMF-113", verification="EXP-D03", evidence_status="CALC",
         current_estimate="a loose sheet under 1 N slides at 0.25-0.5 N (CALC)", trace="", status="proposed"),
    dict(id="REQ-DRV-012", area="drive", title="Clean and replaceable contact",
         requirement="The tyre and the heel pod can be cleaned or replaced by the user; the pod is sealed against paper "
                     "dust and ink",
         rationale="Rolling contacts on paper jam with dust and eraser crumbs (prior art)", source="PAT-33; AMF-117",
         verification="EXP-D10; EXP-D12", evidence_status="LIT", current_estimate="", trace="", status="proposed"),
    dict(id="REQ-DRV-013", area="drive", title="Zero force in the air",
         requirement="Drive torque goes to zero within 20 ms when the wheel load falls below 0.02 N (pen lift); the "
                     "wheel is pre-steered during lifts",
         rationale="Pen-up gaps: nothing to push against; dysgraphic writers stop and lift more often",
         source="CON-38; SIM", verification="EXP-D07", evidence_status="SIM", current_estimate="met in SIM",
         trace="drive/plant.py", status="proposed"),
]

EXPERIMENTS: List[Dict] = [
    dict(id="EXP-D01", title="Tyre-paper friction on six papers",
         purpose="Replace the assumed traction range (0.6-1.2) with measurements; pick the tyre compound",
         method="Horizontal-plane and rolling tribometer (TAPPI T 549 adapted) with a 2 mm wheel locked and rolling; "
                "NBR 70, PU 80 and silicone 50 Shore A tyres; copy 80 g/m2, recycled, school ruled, coated, tracing "
                "and card; 0.3 and 0.6 N; 40 and 60 % RH; 5 repeats",
         measurand="static and kinetic friction coefficient, rolling resistance coefficient",
         pass_line="kinetic mu >= 0.6 on all six papers at 0.3-0.6 N; spread (max/min) reported",
         needs="tribometer or tilting table, 0.01 N load cell, climate box"),
    dict(id="EXP-D02", title="Tyre lateral stiffness and relaxation length",
         purpose="Check k_lat = 1.5 N/mm used by the model and the slip threshold",
         method="Wheel on paper at 0.55 N, lateral displacement stage 0-1 mm, force sensor under the paper",
         measurand="lateral force vs deflection; relaxation length when rolling", pass_line="k_lat >= 1.0 N/mm",
         needs="micrometre stage, 3-axis force sensor"),
    dict(id="EXP-D03", title="Holding the sheet",
         purpose="Know when the drive drags the paper instead of the pen",
         method="Heel drive pulls 0.1-0.6 N on a sheet on wood, laminate and a pad, with and without the writing hand "
                "resting and with the other hand holding",
         measurand="force at which the sheet slides", pass_line=">= 0.6 N with the writing hand resting",
         needs="spring scale or load cell; 3 desks"),
    dict(id="EXP-D04", title="Heel geometry, roll and steering bench",
         purpose="Contact over tilt and roll; steering speed and bandwidth",
         method="3-D printed heel with the sprung wheel pod; pen held in a tilt-roll fixture at 35-75 deg and +/-25 deg "
                "roll; steering step and chirp responses with the Hall angle sensor",
         measurand="contact yes/no, wheel load; steering bandwidth (-3 dB), rate limit",
         pass_line="contact at +/-20 deg roll over 35-75 deg; >= 40 Hz; >= 300 rad/s",
         needs="printed heel, 0620 B motors, fixture"),
    dict(id="EXP-D05", title="Slip detection",
         purpose="Test the paper-sensor-minus-odometry slip rule",
         method="Drive the wheel on six papers; impose slips by lowering the preload or raising the command; record "
                "optical flow and wheel odometry at 1 kHz",
         measurand="detection latency; false flags per 10 s of normal writing motion",
         pass_line="detect within 50 ms; < 1 false flag per 10 s", needs="paper sensor board, encoder, high-speed camera"),
    dict(id="EXP-D06", title="Noise, heat and power",
         purpose="Check the power budget and comfort",
         method="Run recorded drive commands from the SIM tasks on the bench drive; microphone at 30 cm in a quiet "
                "room; thermocouples on windings and sleeve; supply current logging",
         measurand="dB(A); winding and surface temperature; mean electrical power",
         pass_line="<= 35 dB(A); surface <= 41 C; <= 0.15 W", needs="sound meter, thermocouples, power analyser"),
    dict(id="EXP-D07", title="Force cap, stall and lift safety",
         purpose="Show the drive never exceeds its caps and lets go",
         method="Handle clamped to a 3-axis load cell over paper; commanded forces up to saturation; stall the wheel; "
                "lift the pen mid-push; fault injection (sensor loss, motor short)",
         measurand="peak and steady force; time to zero after lift or stall",
         pass_line="steady <= 0.5 N; peak <= 0.6 N; zero within 20 ms of lift", needs="load cell, fixture"),
    dict(id="EXP-D08", title="Guided writing with people (tracing, loops, reversed letters, resist)",
         purpose="Compare heel drive, desk board and nose alone on real hands",
         method="n = 12 adults then children with dysgraphia (ethics approval); crossover of none / nose / board / "
                "heel steer-only / heel steer + drive; tracing, 'write big' loops, b-d reversal; a 'resist' block; "
                "unassisted retention block after 1 day",
         measurand="target error, letters read by the app, felt force (instrumented handle), yields, preference, "
                   "retention",
         pass_line="heel >= board on target error with felt force p95 <= 0.5 N; every participant can overpower it; "
                   "no retention loss vs none",
         needs="prototype, instrumented handle, app recogniser"),
    dict(id="EXP-D09", title="Tremor: constraint and damping",
         purpose="Test steer + brake and the ball damper on tremor and on clean writing",
         method="People with ET (n >= 8): copy and free writing with none / nose / heel steer + brake / heel + nose; "
                "controls without tremor for false correction",
         measurand="ink error, words read, distortion of clean writing",
         pass_line="tremor ink error -20 % with clean-writing distortion <= 100 um", needs="prototype, IMU logging"),
    dict(id="EXP-D10", title="Ink smear and wheel track",
         purpose="Make sure the wheel does not smear ink or mark the paper",
         method="Wheel rolled over fresh gel and ballpoint ink at 0.55 N; 1 page of writing; magnified images",
         measurand="smear length, visible track", pass_line="no ink pick-up; no visible track at 30 cm",
         needs="microscope camera"),
    dict(id="EXP-D11", title="Lead-through and autowrite with relaxed hands",
         purpose="Check that the drive can lead a relaxed hand and that people accept it",
         method="n = 8; relaxed-hand instruction; lead speeds 4-10 mm/s; practice sentence; comfort questionnaire",
         measurand="letters read, pen speed, force, comfort",
         pass_line=">= 70 % letters read at >= 5 mm/s with no discomfort", needs="prototype with drive motor"),
    dict(id="EXP-D12", title="Durability",
         purpose="Tyre wear and friction drift",
         method="Wheel rolled 10 km on copy paper at 0.55 N (about 5000 pages, ASSUMPTION), friction re-measured every "
                "1 km", measurand="mu drift, diameter loss", pass_line="mu within 20 % of new; diameter loss < 0.05 mm",
         needs="rolling rig"),
]

DECISION = (
    "Heel drive for Rev J (proposed): a 2 mm steered wheel with an O-ring tyre at the bottom of a larger skid ring "
    "(contact radius 8.75 mm instead of 6.75 mm), steered about the paper normal through its contact point. Steer-only by "
    "default (passive guidance and tremor constraint); its drive motor is used only in an explicit lead-through or "
    "autowrite mode. Force cap 0.5 N and 0.8 x mu_hat x wheel load; yields to the writer. The driven ball is the "
    "fallback; omni-wheels, braked ball and controllable friction pads are rejected. The front sleeve grows from 15.0 to "
    "18.3 mm at the heel and the paper sensor becomes mandatory. Adopt only after EXP-D01, EXP-D05, EXP-D07 and EXP-D08.")


def write_all(out_dir: Path) -> Dict[str, str]:
    out_dir = Path(out_dir)
    p1 = out_dir / "requirements_rows.csv"
    with open(p1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REQ_HEADER)
        w.writeheader()
        for r in REQUIREMENTS:
            w.writerow(r)
    p2 = out_dir / "experiments.json"
    p2.write_text(json.dumps({"evidence_status": "PROPOSED (protocols; nothing run)", "experiments": EXPERIMENTS,
                              "decision_text": DECISION}, indent=1))
    return {"requirements": str(p1), "experiments": str(p2)}
