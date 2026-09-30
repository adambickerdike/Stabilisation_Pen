"""The learning stage as one resumable step (python3 -m realtrack.chain_after): the FIR, the TCN's training data and its
cross-fitting, the soft-authority searches on the learned models' outputs (the TCN trained on real inputs and ai2's
TCN), then study W's GLG on real inputs.  Every piece is skipped when its output exists."""
from __future__ import annotations

import time

from . import cases as C
from . import learned as LE
from . import netmodel as NM
from . import search as SR
from . import tune as TU


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    if not (LE.MODEL_DIR / "fir_fir_main.json").exists():
        LE.train_fir(C.tuning_specs(), L=128, tag="fir_main", log=log)
    NM.build_train_set(log=log)
    NM.selection_arrays(log=log)
    if not (NM.MODEL_DIR / "net_main_crossfit.json").exists():
        NM.cross_fit(tag="net_main", log=log)
    if not (TU.TUNE_DIR / "auth_net_main.json").exists():
        TU.auth_search({"family": "net", "params": {"tag": "net_main", "fold": "auto"}}, n_random=36, n_local=18,
                       seed=61, tag="net_main", log=log)
    if not (TU.TUNE_DIR / "auth_ai2tcn.json").exists():
        TU.auth_search({"family": "ai2tcn", "params": {}}, n_random=36, n_local=18, seed=67, tag="ai2tcn", log=log)
    log("[chain] learn done")
    SR.glg_search_resumable(log=log)
    log("[chain] glg done")


if __name__ == "__main__":
    main()
