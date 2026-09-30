"""After the freeze and the analyses: the one test run, the pictures, the sim2 check and the report
(python3 -m realtrack.final).  Every step is resumable (per-case caches), so a container restart loses at most one case."""
from __future__ import annotations

import json
import time

from . import BUILD_DIR


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main(steps=("test", "pictures", "sim2", "report")):
    from . import test as T
    if "test" in steps:
        T.run(log=log)
        log("[final] test done")
    if "pictures" in steps:
        T.picture_runs(log=log)
        log("[final] pictures done")
    if "sim2" in steps:
        from . import sim2check as S2
        p = BUILD_DIR / "sim2.json"
        if not p.exists():
            out = S2.run(log=log)
            p.write_text(json.dumps(summarize_sim2(out), default=float))
        log("[final] sim2 done")
    if "report" in steps:
        from . import report as RP
        RP.write(log=log)
        from . import doc
        doc.main()
        log("[final] report done")


def summarize_sim2(out) -> dict:
    """Per cell: the new design's ink-error ratio to the device-off run and sim2j's G4 ('nose') and perfect knowledge
    ('oracle') ratios for the same writer, seed and cell; the clean runs' false correction."""
    rows = []
    for r in out["rows"]:
        ref = r["sim2j_rows"]
        none = ref.get("none") or {}
        rr = {"f0": r["f0"], "amp_mm": r["amp_mm"], "new_ratio": r["new"].get("ratio"),
              "new_ink_err_um": r["new"].get("ink_err_um"), "new_words_app": r["new"].get("words_app"),
              "new_moved_um": r["new"].get("moved_vs_clean_um"),
              "none_ink_err_um_rerun": (r.get("none_rerun") or {}).get("ink_err_um"),
              "none_ink_err_um_sim2j": none.get("ink_err_um"), "none_words_app": none.get("words_app")}
        for c in ("nose", "oracle", "tcn"):
            v = ref.get(c) or {}
            rr[f"{c}_ratio"] = v.get("ratio")
            rr[f"{c}_words_app"] = v.get("words_app")
            rr[f"{c}_moved_um"] = v.get("moved_vs_clean_um")
        rows.append(rr)
    return {"rows": rows, "design": out.get("design"),
            "label": "SIMULATION (sim2, MuJoCo) with SYNTHETIC writer and tremor (sim2j's ET grid, writer 0, seed 200); "
                     "replay of the frozen design on the device-off run's recorded sensor streams (sim2j/learned_replay "
                     "method); G4, oracle and ai2-TCN rows are sim2j's own cached test rows"}


if __name__ == "__main__":
    main()
