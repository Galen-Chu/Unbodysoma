"""Small numerical helpers shared by module implementations."""

from __future__ import annotations

import math
import random


def relax(current: float, target: float, dt: float, tau: float) -> float:
    """Exact first-order approach of ``current`` toward ``target`` with time constant ``tau``."""
    return target + (current - target) * math.exp(-dt / tau)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def ou_step(x: float, dt: float, tau: float, sigma: float, rng: random.Random) -> float:
    """Exact Ornstein-Uhlenbeck update: mean 0, stationary SD ``sigma``, correlation time ``tau``.

    Unlike white noise, successive values are correlated (autocorrelation
    ``exp(-lag / tau)``), and the statistics do not depend on the step size.
    See docs/VARIABILITY.md §5.2.
    """
    a = math.exp(-dt / tau)
    return x * a + sigma * math.sqrt(1.0 - a * a) * rng.gauss(0.0, 1.0)
