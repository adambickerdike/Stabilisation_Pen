"""Delayed relative refill-slide contact channel for the generic servo.

The sensor measures displacement relative to the mechanical front stop at
acquisition. It never compares an old sample against a future moving stop.
RevJ uses its existing firmware channel instead of this separate sampler.
"""
from collections import deque
import numpy as np


class SlideContact:
    def __init__(self, pm, seed=0):
        self.pm = pm
        self.s = pm.cfg.sensors
        self.rng = np.random.default_rng(seed)
        self.jq = pm.jnt_qadr("refill_s")
        self.joint = pm.ids["jnt:refill_s"]
        self.queue = deque()
        self.next_sample = 0.0
        self.last_contact = False
        self.last_acquired = None

    def read(self, now):
        if now + 1e-12 >= self.next_sample:
            relative = self.pm.d.qpos[self.jq] - self.pm.m.jnt_range[self.joint, 0]
            relative += self.rng.normal(0., self.s.slide_noise)
            self.queue.append((now, now + self.s.slide_latency, relative > self.s.slide_thr))
            while self.next_sample <= now + 1e-12:
                self.next_sample += 1. / self.s.slide_rate
        while self.queue and self.queue[0][1] <= now + 1e-12:
            self.last_acquired, _, self.last_contact = self.queue.popleft()
        return bool(self.last_contact)
