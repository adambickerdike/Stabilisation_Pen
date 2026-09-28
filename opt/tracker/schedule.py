"""Event bookkeeping of fusion.estimators._akf_run that depends only on the sample clocks (no filter arithmetic).

For every 0.5 ms tick the numba AKF processes (in this order): the accelerometer samples that became available
(at most one per tick with the 2-sample FIFO average at 1.92 kHz), the page-sensor samples that became available
(at most one per tick up to 2 kHz; each valid one rolls the filter back to the snapshot of the last accelerometer
sample acquired no later than the page sample, applies the page update at its acquisition time and re-applies the
later accelerometer samples), then the frequency tracker and the output.  Which sample is processed when, the
rollback target, the re-applied samples, every prediction interval dt, the filter time tf, the position re-anchoring
after a gap and the frequency tracker's "filter time advanced" flags are functions of the sample times and the
page validity only.  They are computed here once per recording (numpy) and replayed by opt.tracker.torch_akf,
which then only does the arithmetic.  Mirrors _akf_run line by line; unit-tested against it through the filter output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from fusion import estimators as ES
from fusion.sensors import Streams

HIST = ES.HIST


@dataclass
class Schedule:
    K: int                      # ticks
    Ts: float                   # tick period
    tick_t: np.ndarray          # (K,)
    # accelerometer event per tick (at most one)
    acc_ev: np.ndarray          # (K,) bool
    acc_first: np.ndarray       # (K,) bool: first sample (filter start)
    acc_dt: np.ndarray          # (K,) prediction interval before the update (0: no prediction)
    acc_ta: np.ndarray          # (K,) filter time of the sample (acquisition time - acc_gd)
    acc_y: np.ndarray           # (K, 2) block-averaged page-frame nib acceleration
    # page event per tick (at most one); only the ones the filter uses (valid, started, snapshot exists)
    pg_ev: np.ndarray           # (K,) bool
    pg_snap: np.ndarray         # (K,) int: tick index of the snapshot rolled back to
    pg_dt: np.ndarray           # (K,) prediction interval snapshot -> page acquisition time (0: none)
    pg_gap: np.ndarray          # (K,) bool: position re-anchoring instead of the update (first sample / after a gap)
    pg_y: np.ndarray            # (K, 2)
    pg_nre: np.ndarray          # (K,) number of re-applied accelerometer samples
    re_tick: np.ndarray         # (K, R) tick indices of the re-applied samples (-1 beyond pg_nre)
    re_dt: np.ndarray           # (K, R) their prediction intervals
    # per tick after all events
    tf: np.ndarray              # (K,) filter time
    started: np.ndarray         # (K,) bool
    fr_adv: np.ndarray          # (K,) bool: tf advanced since the last phase reference (frequency update allowed)
    fr_have: np.ndarray         # (K,) bool: a phase reference exists (before this tick)
    fr_upd: np.ndarray          # (K,) bool: phase reference replaced at this tick
    fr_dtp: np.ndarray          # (K,) tf - tf_prev (the interval of the phase-rate measurement)
    D: int                      # largest rollback depth in ticks (page tick - snapshot tick)
    R: int                      # largest number of re-applied samples

    @property
    def n_acc(self) -> int:
        return int(self.acc_ev.sum())


def acc_samples(st: Streams, acc_decim: int = 2):
    return ES._block_average(st.acc_t, st.acc_av, st.acc, acc_decim)


def build(st: Streams, acc_decim: int = 2, acc_gd: float = 1.04e-3, gap_reset: float = 0.03, use_pos: bool = True,
          r_max: Optional[int] = None) -> Schedule:
    """Replay the sample handling of _akf_run (no arithmetic) and record it per tick."""
    ta_all, tav, y = acc_samples(st, acc_decim)
    tick_t = np.asarray(st.tick_t, float)
    K = len(tick_t)
    Ts = float(tick_t[1] - tick_t[0])
    na, npos = len(ta_all), len(st.pos_t)
    acc_ev = np.zeros(K, bool); acc_first = np.zeros(K, bool); acc_dt = np.zeros(K); acc_ta = np.zeros(K)
    acc_y = np.zeros((K, 2))
    pg_ev = np.zeros(K, bool); pg_snap = np.full(K, -1, np.int64); pg_dt = np.zeros(K); pg_gap = np.zeros(K, bool)
    pg_y = np.zeros((K, 2)); pg_nre = np.zeros(K, np.int64)
    re_list: List[List] = [[] for _ in range(K)]
    tf_k = np.zeros(K); started_k = np.zeros(K, bool)
    fr_adv = np.zeros(K, bool); fr_have = np.zeros(K, bool); fr_upd = np.zeros(K, bool); fr_dtp = np.zeros(K)
    snap_t: List[float] = []          # h_t per accelerometer sample (processing order)
    snap_tick: List[int] = []         # tick at which it was processed
    ia = ip = 0
    tf = 0.0
    started = False
    last_pos_t = -1.0
    have_phase = False
    tf_prev = 0.0
    for k in range(K):
        t = tick_t[k]
        n_this = 0
        while ia < na and tav[ia] <= t:
            n_this += 1
            if n_this > 1:
                raise ValueError("more than one accelerometer sample in a tick: use acc_decim >= 2 at 3.84 kHz")
            ta = ta_all[ia] - acc_gd
            if not started:
                started = True
                tf = ta
                acc_first[k] = True
            dt = ta - tf
            if dt > 0:
                tf = ta
            acc_ev[k] = True
            acc_dt[k] = max(dt, 0.0)
            acc_ta[k] = ta
            acc_y[k] = y[ia]
            snap_t.append(tf)
            snap_tick.append(k)
            ia += 1
        n_pg = 0
        while ip < npos and st.pos_av[ip] <= t:
            if st.pos_ok[ip] > 0.5 and use_pos and started and len(snap_t) > 0:
                n_pg += 1
                if n_pg > 1:
                    raise ValueError("more than one page-sensor sample in a tick")
                tp = st.pos_t[ip]
                nh = len(snap_t)
                lo = max(0, nh - HIST)
                jj = nh - 1
                while jj >= lo and snap_t[jj] > tp:
                    jj -= 1
                if jj >= lo:
                    tf = snap_t[jj]
                    gap = last_pos_t < 0 or tp - last_pos_t > gap_reset
                    dt = tp - tf
                    if dt > 0:
                        tf = tp
                    pg_ev[k] = True
                    pg_snap[k] = snap_tick[jj]
                    pg_dt[k] = max(dt, 0.0)
                    pg_gap[k] = gap
                    pg_y[k] = st.pos[ip]
                    last_pos_t = tp
                    for q in range(jj + 1, nh):
                        dtq = snap_t[q] - tf
                        if dtq > 0:
                            tf = snap_t[q]
                        re_list[k].append((snap_tick[q], max(dtq, 0.0)))
                    pg_nre[k] = nh - 1 - jj
            ip += 1
        # frequency tracker flags (the state-dependent conditions are evaluated by the torch filter)
        fr_have[k] = have_phase
        adv = tf > tf_prev + 1e-9
        fr_adv[k] = adv
        fr_dtp[k] = tf - tf_prev
        if adv or not have_phase:
            fr_upd[k] = True
            tf_prev = tf
            have_phase = True
        tf_k[k] = tf
        started_k[k] = started
    R = int(max(1, max(len(r) for r in re_list)))
    if r_max is not None:
        R = max(R, r_max)
    re_tick = np.full((K, R), -1, np.int64)
    re_dt = np.zeros((K, R))
    for k, lst in enumerate(re_list):
        for j, (q, d) in enumerate(lst):
            re_tick[k, j] = q
            re_dt[k, j] = d
    D = int(max(0, np.max(np.where(pg_ev, np.arange(K) - pg_snap, 0))))
    return Schedule(K=K, Ts=Ts, tick_t=tick_t, acc_ev=acc_ev, acc_first=acc_first, acc_dt=acc_dt, acc_ta=acc_ta,
                    acc_y=acc_y, pg_ev=pg_ev, pg_snap=pg_snap, pg_dt=pg_dt, pg_gap=pg_gap, pg_y=pg_y, pg_nre=pg_nre,
                    re_tick=re_tick, re_dt=re_dt, tf=tf_k, started=started_k, fr_adv=fr_adv, fr_have=fr_have,
                    fr_upd=fr_upd, fr_dtp=fr_dtp, D=D, R=R)
