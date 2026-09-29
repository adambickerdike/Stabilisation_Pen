"""Dataset registry: what each recording set is, who made it, its licence, and what this project may redistribute.

Every entry was opened by study R on 2026-09-29 (files downloaded through the environment's proxy with TLS
verification on).  Raw files live in realdata/build/raw/ (git-ignored) and are never committed.  ``redistribute``
says what may go into results/realdata/ (committed):
  * "excerpts"   CC BY 4.0: short, attributed excerpts (e.g. the ink of a before/after picture) and statistics;
  * "statistics" statistics and fitted parameters only (no trajectories, no signals, no personal data);
  * "nothing"    not used for committed outputs.
``fetch(key)`` downloads a dataset again (resumable); ``status()`` reports which files are present, with sha256.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import RAW_DIR


@dataclass
class Source:
    key: str
    name: str
    citation: str
    url: str
    doi: str
    licence: str
    licence_url: str
    redistribute: str                 # excerpts | statistics | nothing
    role: str                          # what study R uses it for
    content: str                       # what the recordings are (as documented by the authors)
    units: str                         # units as documented, and the calibration used here
    files: Dict[str, str] = field(default_factory=dict)   # local file (relative to RAW_DIR) -> download URL
    ledger: str = ""                   # ledger ids (existing and proposed)
    notes: str = ""

    def describe(self) -> Dict:
        d = asdict(self)
        d.pop("files")
        return d


_UCI = "https://archive.ics.uci.edu/static/public"
_PADS = "https://physionet.org/files/parkinsons-disease-smartwatch/1.0.0"
_HPD = "https://wwwp.fc.unesp.br/~papa/pub/datasets/Handpd"

SOURCES: Dict[str, Source] = {
    "uci_spiral": Source(
        key="uci_spiral", name="UCI Parkinson Disease Spiral Drawings Using Digitized Graphics Tablet",
        citation=("Isenkul ME, Sakar BE, Kursun O. Improved spiral test using digitized graphics tablet for monitoring "
                  "Parkinson's disease. ICEHTM 2014:171-175; dataset donated to the UCI Machine Learning Repository "
                  "2017 (doi 10.24432/C5Q01S)"),
        url="https://archive.ics.uci.edu/dataset/395", doi="10.24432/C5Q01S", licence="CC BY 4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/", redistribute="excerpts",
        role="PD kinetic tremor at the pen tip in 2-D (tip displacement while drawing spirals); controls; severity "
             "classes; tremor waveforms of the generator (PD)",
        content=("Wacom Cintiq 12WX pen display.  hw_dataset: 25 PD + 15 controls; new_dataset: 37 PD.  Columns X; Y; Z; "
                 "Pressure; GripAngle; Timestamp; Test ID (0 static spiral, 1 dynamic spiral, 2 circles around a point)"),
        units=("X, Y integers in screen pixels (DERIVED: range 16-572 matches the 1280 x 800 display, not the 0.005 mm "
               "tablet grid); converted with the Cintiq 12WX pixel pitch 0.204 mm (MFR, Wacom manual).  Timestamp in ms "
               "(steps of 7-10, about 130-140 Hz; manual: maximum report rate 133 points/s)"),
        files={"uci_pd_spiral.zip": f"{_UCI}/395/parkinson+disease+spiral+drawings+using+digitized+graphics+tablet.zip"},
        ledger="PDT-30 (existing); PDT-75 (proposed, this study's tip-tremor re-analysis); CON-84 (MFR tablet)"),
    "newhandpd": Source(
        key="newhandpd", name="NewHandPD (BiSP smart-pen signals)",
        citation=("Pereira CR, Weber SAT, Hook C, Rosa GH, Papa JP. Deep learning-aided Parkinson's disease diagnosis "
                  "from handwritten dynamics. SIBGRAPI 2016 (NewHandPD); dataset page of JP Papa, UNESP"),
        url=f"{_HPD}/", doi="", licence="no licence stated (the page asks users to cite "
        "SIBGRAPI-2016)", licence_url="", redistribute="statistics",
        role="acceleration spectra of an instrumented pen in PD and healthy writers (frequency, peak-to-floor ratio, "
             "band acceleration); no positions",
        content=("BiSP pen ('Pentrics Alberich1'), 1000 samples/s, 6 channels: CH1 microphone, CH2 finger grip, CH3 axial "
                 "refill pressure, CH4-6 'tilt and acceleration' X, Y, Z (sensor at the pen's rear end, paper Fig. 3).  "
                 "31 PD (372 files) and 35 healthy (420 files): 4 spirals, 4 meanders, circle on paper (circA), circle "
                 "in the air (circB), diadochokinesis right (sigDiaA) and left (sigDiaB)"),
        units=("uncalibrated sensor outputs (volt-like, 0.0165 steps on CH4-6).  CH4-6 are calibrated here to m/s^2 by "
               "a DERIVED gravity calibration (offset and gain per axis fitted so that |a| = 1 g in quasi-static samples "
               "pooled over recordings of the same pen; calib.gravity_fit)"),
        files={"newhandpd_PatientSignal.zip": f"{_HPD}/NewPatients/PatientSignal.zip",
               "newhandpd_HealthySignal.zip": f"{_HPD}/NewHealthy/HealthySignal.zip",
               "newhandpd_NewSpiral.csv": f"{_HPD}/NewSpiral.csv",
               "opf-sibgrapi16.pdf": "http://sibgrapi.sid.inpe.br/col/sid.inpe.br/sibgrapi/2016/07.08.22.47/doc/opf-sibgrapi16.pdf"},
        ledger="PDT-29 (existing); PDT-76 (proposed, this study's spectra)",
        notes="File headers carry a person ID number, age, weight, height and smoking status: never copied to results."),
    "zenodo_et": Source(
        key="zenodo_et", name="Accelerometry recordings from essential tremor patients",
        citation=("Pardo-Valencia J, Ammann C, Foffani G. Accelerometry recordings from essential tremor patients "
                  "[dataset]. Zenodo, 2026, record 19130599"),
        url="https://zenodo.org/records/19130599", doi="10.5281/zenodo.19130599", licence="CC BY 4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/", redistribute="excerpts",
        role="ET rest and postural tremor waveforms (frequency, wander, envelope, harmonics); tremor waveforms of the "
             "generator (ET).  Amplitude is not calibrated, so the generator scales it to a severity class",
        content=("29 ET patients, both hands (58), one accelerometer axis on the dorsum of the hand, rest and posture "
                 "(arms extended), 100 s each (73.4 +/- 11.1 s after artefact removal), band-pass 2 Hz-2 kHz, x1000 "
                 "(Digitimer D360), 5000 samples/s (CED 1401); clinical file: Fahn-Tolosa-Marin total, age, duration"),
        units="arbitrary units (ADC volts after x1000; sensor sensitivity not published; the same lab reports amplitude "
              "in log10 a.u., LIT PDT-79)",
        files={"zenodo_et_acc/acc_signal_database.mat": "https://zenodo.org/api/records/19130599/files/acc_signal_database.mat/content",
               "zenodo_et_acc/clinical_data.mat": "https://zenodo.org/api/records/19130599/files/clinical_data.mat/content",
               "zenodo_et_acc/README.txt": "https://zenodo.org/api/records/19130599/files/README.txt/content"},
        ledger="PDT-77 (proposed); PDT-79 (proposed, the lab's method paper)"),
    "pads": Source(
        key="pads", name="PADS - Parkinson's Disease Smartwatch dataset (PhysioNet 1.0.0)",
        citation=("Varghese J, Brenner A, Plagwitz L, van Alen C, Fujarski M, Warnecke T. PADS - Parkinsons Disease "
                  "Smartwatch dataset (version 1.0.0). PhysioNet 2024. doi 10.13026/m0w9-zx22; Varghese J et al. "
                  "Machine learning in the Parkinson's disease smartwatch (PADS) dataset. npj Parkinsons Dis 10:9 (2024)"),
        url="https://physionet.org/content/parkinsons-disease-smartwatch/1.0.0/", doi="10.13026/m0w9-zx22",
        licence="CC BY-NC-SA 4.0 (PhysioNet open access)",
        licence_url="https://creativecommons.org/licenses/by-nc-sa/4.0/", redistribute="statistics",
        role="calibrated wrist tremor (acceleration in g) of ET, PD and healthy people in rest, postural and kinetic "
             "tasks: amplitude at the wrist (mm, CALC), rest/action behaviour, 3-D shape (ellipticity)",
        content=("469 people (276 PD, 28 ET, 79 healthy, others), two Apple Watch Series 4 (both wrists), 100 samples/s, "
                 "11 tasks of 10-20 s (rest, rest with serial sevens, arms lifted, 1 kg weight, drinking, crossing arms, "
                 "touching the nose, entrainment).  Used here: all 28 ET, all 79 healthy and 80 randomly drawn PD "
                 "(seeded), 'preprocessed' files (gravity removed by the authors' L1 trend filter, first 0.48 s cut)"),
        units="acceleration in g and rotation in rad/s (documented)",
        files={"pads/file_list.csv": f"{_PADS}/preprocessed/file_list.csv", "pads/SHA256SUMS.txt": f"{_PADS}/SHA256SUMS.txt"},
        ledger="PDT-78 (proposed)",
        notes="Non-commercial, share-alike: statistics only in committed files; no signals."),
    "chartraj": Source(
        key="chartraj", name="UCI Character Trajectories",
        citation="Williams BH. Character Trajectories [dataset]. UCI Machine Learning Repository, 2008 (doi 10.24432/C58G7V)",
        url="https://archive.ics.uci.edu/dataset/175", doi="10.24432/C58G7V", licence="CC BY 4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/", redistribute="excerpts",
        role="real letters with real timing (one adult writer): the committed before/after pictures (letters of the "
             "writer composed into a sentence); the reproduction of LIT CON-25",
        content="2858 single-pen-down lower-case characters (20 letters) of one writer, WACOM tablet, 200 samples/s, "
                "x and y velocity and pen force, Gaussian smoothed (sigma 2 samples) by the authors",
        units=("velocity in tablet units per sample (not documented).  Scale used here: the one of LIT CON-25 (0.005 mm "
               "per unit, giving 13.9 mm median character height), then the letters are resized to a normal letter "
               "height (ASSUMPTION, LIT PDT-06); timing is kept"),
        files={"chartraj.zip": f"{_UCI}/175/character+trajectories.zip"}, ledger="CON-25 (existing); CON-82 (proposed)"),
    "uji": Source(
        key="uji", name="UJI Pen Characters (Version 2)",
        citation=("Prat F, Castro MJ, Llorens D, Marzal A, Vilar JM. UJIpenchars2 [dataset], UCI 2009; Llorens D et al. "
                  "The UJIpenchars database: a pen-based database of isolated handwritten characters. LREC 2008"),
        url="https://archive.ics.uci.edu/dataset/177", doi="10.24432/C5FG8S", licence="CC BY 4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/", redistribute="excerpts",
        role="real letter shapes and sizes of 60 writers (no timing): letter-size statistics",
        content="11,640 isolated characters, 60 writers, 2 repetitions, Toshiba Portege M400 tablet PC",
        units="100 units per millimetre (file header); no time stamps (LREC 2008 paper: 'without ... timing information')",
        files={"uji2.zip": f"{_UCI}/177/uji+pen+characters+version+2.zip"}, ledger="CON-48 (existing); CON-83 (proposed)"),
    "brush": Source(
        key="brush", name="BRUSH (BRown University Stylus Handwriting)",
        citation=("Kotani A, Tellex S, Tompkin J. Generating handwriting via decoupled style descriptors. ECCV 2020, "
                  "pp. 764-780 (doi 10.1007/978-3-030-58610-2_45); BRUSH dataset, refined release"),
        url="https://github.com/brownvc/decoupled-style-descriptors", doi="10.1007/978-3-030-58610-2_45",
        licence="non-commercial research use only (README and dsd.cs.brown.edu); cite the ECCV paper",
        licence_url="https://github.com/brownvc/decoupled-style-descriptors#terms-of-use", redistribute="statistics",
        role="real words with real pen-down timing from 170 writers: the writing inputs of the headline comparison "
             "(aggregate numbers committed; ink not committed); scale-free kinematics",
        content=("27,649 samples of short prescribed sentences (2-4 words) written with a stylus in a 120 x 748 pixel "
                 "box; points resampled every 10 ms by the authors (pen-down only, end-of-stroke flags); per-point "
                 "character labels"),
        units=("screen pixels of different devices (not documented) -> the physical size of each writer is DERIVED: the "
               "mean height of the writer's 'T', 'p' and 'a' is set to a draw from the healthy-adult distribution of "
               "LIT PDT-06 (median 5.0 mm, IQR 1.4 mm); pen-up moves are not recorded (ASSUMPTION timing, writinglib)"),
        files={"brush_refined_BRUSH.zip": "https://drive.usercontent.google.com/download?id=1NIIXDfmpUhI6i80Dg2363PIdllY7FRVQ&export=download&confirm=t"},
        ledger="OPT-30 (existing); CON-80 (proposed, this study's kinematics)",
        notes="Commercial use requires permission from Prof. J. Tompkin (Brown University)."),
    "unipen": Source(
        key="unipen", name="UNIPEN train_r01_v07 (International Unipen Foundation)",
        citation=("Guyon I, Schomaker L, Plamondon R, Liberman M, Janet S. UNIPEN project of on-line data exchange and "
                  "recognizer benchmarks. ICPR 1994; Unipen data set of on-line handwriting - train_r01_v07, Zenodo "
                  "record 1195803"),
        url="https://zenodo.org/records/1195803", doi="10.5281/zenodo.1195803",
        licence=("research use only (iUF notice inside the data: 'permission is hereby granted to use the data for research "
                 "purposes; it is not allowed to distribute this data for commercial purposes'); the Zenodo page tags CC "
                 "BY 4.0 - the stricter terms are applied"),
        licence_url="https://zenodo.org/records/1195803", redistribute="statistics",
        role="real sentences and words written on paper or tablets with timing and physical units: writing speed and "
             "kinematics in mm/s (validation only)",
        content="categories 6-8: isolated words and free text from many contributors (e.g. dar2: CalComp DrawingBoard II, "
                "ballpoint on A4 paper, 200 samples/s, 0.01 mm/unit)",
        units="per data set: .X_POINTS_PER_MM or .X_POINTS_PER_INCH and .POINTS_PER_SECOND in the headers",
        files={"unipen/unipen-CDROM-train_r01_v07.tgz": "https://zenodo.org/api/records/1195803/files/unipen-CDROM-train_r01_v07.tgz/content"},
        ledger="CON-81 (proposed)",
        notes="Headers contain writers' names: never copied to results."),
}

NOT_USED = {
    "iam_ondb": {"name": "IAM On-Line Handwriting Database (IAM-OnDB)", "url": "https://fki.tic.heia-fr.ch/databases/iam-on-line-handwriting-database",
                 "why": "requires registration (not done, as instructed); the dataset to request for English sentence "
                        "trajectories written on a whiteboard (LIT OPT-29)"},
    "diagramo": {"name": "DiaGraMo: multimodal Czech online handwriting of 276 children (161 with dysgraphia)",
                 "url": "https://zenodo.org/records/21236910",
                 "why": "CC BY 4.0, Wacom Cintiq 16 at about 167 Hz, sentences, hover data; found late, 1.36 GB; children "
                        "writing Czech; the natural source for the poor-handwriting and dyslexia studies (EXP-R04)"},
    "pahaw": {"name": "PaHaW Parkinson's disease handwriting database (Drotar et al.)",
              "url": "https://bdalab.utko.fee.vutbr.cz/", "why": "available on request with a licence agreement (not requested)"},
}


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def path(key: str, name: Optional[str] = None) -> Path:
    s = SOURCES[key]
    return RAW_DIR / (name or next(iter(s.files)))


def present(key: str) -> bool:
    return all((RAW_DIR / f).exists() for f in SOURCES[key].files)


def fetch(key: str, force: bool = False, timeout: int = 3600) -> List[str]:
    """Download the files of one source into realdata/build/raw (curl, resumable, TLS verified by the proxy's CA)."""
    out = []
    for rel, url in SOURCES[key].files.items():
        p = RAW_DIR / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not force:
            out.append(str(p))
            continue
        cmd = ["curl", "-sS", "-L", "-C", "-", "--retry", "5", "--retry-delay", "5", "--max-time", str(timeout),
               "-o", str(p), url]
        subprocess.run(cmd, check=True)
        out.append(str(p))
    return out


def status(with_hash: bool = False) -> Dict[str, Dict]:
    """Presence (and optionally sha256) of every registered file; the result JSON records it as provenance."""
    rep = {}
    for key, s in SOURCES.items():
        files = {}
        for rel in s.files:
            p = RAW_DIR / rel
            e = {"present": p.exists()}
            if p.exists():
                e["bytes"] = p.stat().st_size
                if with_hash:
                    e["sha256"] = sha256(p)
            files[rel] = e
        rep[key] = {"licence": s.licence, "redistribute": s.redistribute, "files": files}
    return rep


def table() -> List[Dict]:
    """The dataset table of docs/real_data.md."""
    return [s.describe() for s in SOURCES.values()]


if __name__ == "__main__":
    print(json.dumps(status(True), indent=1))
