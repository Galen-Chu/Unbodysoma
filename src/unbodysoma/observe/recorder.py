"""Recording signals over time for inspection, plotting and regression tests."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from ..core import SignalBus

_EPS = 1e-9


class Recorder:
    """Engine observer that samples the given signals every ``every`` seconds."""

    def __init__(self, keys: Iterable[str], every: float = 1.0) -> None:
        self.keys = tuple(keys)
        self.every = every
        self.rows: list[tuple[float, ...]] = []
        self._next = 0.0

    def __call__(self, t: float, bus: SignalBus) -> None:
        if t + _EPS >= self._next:
            self.rows.append((t, *(bus.read(k) for k in self.keys)))
            self._next += self.every

    def column(self, key: str) -> list[float]:
        index = 1 + self.keys.index(key)
        return [row[index] for row in self.rows]

    def times(self) -> list[float]:
        return [row[0] for row in self.rows]

    def to_csv(self, path: str | Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("time", *self.keys))
            writer.writerows(self.rows)

    def table(self, headers: Iterable[str] | None = None, precision: int = 2) -> str:
        headers = ("t", *(headers or self.keys))
        width = max(8, *(len(h) for h in headers))
        lines = ["  ".join(h.rjust(width) for h in headers)]
        for row in self.rows:
            lines.append("  ".join(f"{v:{width}.{precision}f}" for v in row))
        return "\n".join(lines)
