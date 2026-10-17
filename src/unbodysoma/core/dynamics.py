"""Small numerical helpers shared by module implementations."""

from __future__ import annotations

import math


def relax(current: float, target: float, dt: float, tau: float) -> float:
    """Exact first-order approach of ``current`` toward ``target`` with time constant ``tau``."""
    return target + (current - target) * math.exp(-dt / tau)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x
