"""Causal angular velocity from timestamped Hall angle samples.

Filtered backward differences use acquisition intervals, never call intervals.
A held sample is not a new measurement. The readout reports age and validity;
the servo decides how to fail when feedback becomes stale.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class VelocityReading:
    value: float
    age_s: float
    valid: bool


class HallVelocity:
    def __init__(self, cutoff_hz=300.0):
        if cutoff_hz <= 0:
            raise ValueError("velocity cutoff must be positive")
        self.cutoff_hz = float(cutoff_hz)
        self.t = None
        self.angle = 0.0
        self.velocity = 0.0
        self.n_updates = 0

    def observe(self, acquired_at, angle):
        acquired_at, angle = float(acquired_at), float(angle)
        if not math.isfinite(acquired_at) or not math.isfinite(angle):
            raise ValueError("Hall samples must be finite")
        if self.t is not None:
            if acquired_at < self.t:
                raise ValueError("Hall samples must arrive in acquisition order")
            if acquired_at == self.t:
                return False
            dt = acquired_at - self.t
            raw = (angle - self.angle) / dt
            alpha = -math.expm1(-2.0 * math.pi * self.cutoff_hz * dt)
            self.velocity += alpha * (raw - self.velocity)
        self.t, self.angle = acquired_at, angle
        self.n_updates += 1
        return True

    def read(self, now, max_age_s):
        if self.t is None:
            return VelocityReading(0.0, math.inf, False)
        age = float(now) - self.t
        valid = -1e-12 <= age <= max_age_s + 1e-12 and self.n_updates >= 2
        return VelocityReading(self.velocity, age, bool(valid))
