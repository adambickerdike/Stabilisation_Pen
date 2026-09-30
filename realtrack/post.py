"""After the searches: the freeze, then the analyses that explain the results (python3 -m realtrack.post).
Resumable: each step is skipped when its output exists."""
from __future__ import annotations

import json
import time

from . import BUILD_DIR
from . import analysis as AN
from . import freeze as FZ
from . import mcu as MC


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    fr = FZ.run(log=log)
    p = BUILD_DIR / "chosen_mcu.json"
    if not p.exists():
        p.write_text(json.dumps(MC.chosen(fr), default=float))
    AN.learned(log=log)
    AN.separability(log=log)
    AN.delay(fr["chosen"], log=log)
    AN.raw_clean(log=log)
    AN.int8_ai2tcn(log=log)
    AN.writer_stats(log=log)
    log("[post] done")


if __name__ == "__main__":
    main()
