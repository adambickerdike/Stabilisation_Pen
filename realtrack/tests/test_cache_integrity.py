"""The detector cache must not reuse a different writer with matching endpoints."""
from types import SimpleNamespace
import numpy as np


def test_gate_cache_hashes_interior_samples(monkeypatch):
    from realtrack import estimators as E
    E._RATIO.clear()
    calls = []
    def detector(st, params):
        calls.append(st.pos.copy())
        return {"ratio": np.repeat(st.pos[1, 0], 3)}
    monkeypatch.setattr(E, "det_ratio", detector)
    t = np.arange(3, dtype=float)
    def stream(x):
        return SimpleNamespace(tick_t=t, pos_t=t, pos_av=t, pos=np.array([[0., 0.], [x, 0.], [1., 0.]]),
                               pos_ok=np.ones(3), con_t=t, con_av=t, con=np.ones(3))
    a = E._ratio_cached(stream(0.1))
    b = E._ratio_cached(stream(0.9))
    assert len(calls) == 2
    assert np.all(a == 0.1) and np.all(b == 0.9)
    E._ratio_cached(stream(0.9))
    assert len(calls) == 2
