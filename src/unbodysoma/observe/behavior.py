"""Behavioural analysis of recorded runs: episodes, daily summaries, time budgets."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

_SECONDS_PER_DAY = 86400.0


@dataclass(frozen=True)
class Episode:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def episodes(times: Sequence[float], values: Sequence[float], threshold: float = 0.5) -> list[Episode]:
    """Maximal stretches where ``value > threshold`` (an episode still running at the end is closed there)."""
    if len(times) != len(values):
        raise ValueError("times and values must have the same length")
    found: list[Episode] = []
    start: float | None = None
    for t, v in zip(times, values, strict=True):
        if v > threshold and start is None:
            start = t
        elif v <= threshold and start is not None:
            found.append(Episode(start, t))
            start = None
    if start is not None:
        found.append(Episode(start, times[-1]))
    return found


def per_day(found: Sequence[Episode], days: int) -> list[int]:
    """Number of episodes starting on each simulated day (day 0 starts at t = 0)."""
    return [sum(1 for e in found if d * _SECONDS_PER_DAY <= e.start < (d + 1) * _SECONDS_PER_DAY) for d in range(days)]


def time_fraction(values: Sequence[float], threshold: float) -> float:
    """Share of samples with ``value > threshold``."""
    return sum(1 for v in values if v > threshold) / len(values) if values else 0.0
