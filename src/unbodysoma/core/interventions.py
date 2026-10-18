"""Experimental interventions applied by the engine. See docs/adr/0005-read-only-observation-logged-intervention.md.

Interventions are created through ``Engine.clamp`` / ``Engine.lesion`` (never by
writing to the bus directly), so every one of them is scheduled, applied and
logged by the engine and is therefore part of the reproducible run.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

LESION_MODES = ("silence", "freeze")


@dataclass(frozen=True)
class Clamp:
    """Force signal ``key`` to ``value`` during ``start <= t < end``.

    Readers see the clamped value; the writing module keeps its own internal
    state (like stimulating an axon rather than rewiring the neuron).
    """

    id: int
    key: str
    value: float
    start: float = 0.0
    end: float = math.inf

    def active(self, t: float) -> bool:
        return self.start <= t < self.end

    def describe(self) -> dict[str, Any]:
        return {"type": "clamp", **asdict(self)}


@dataclass(frozen=True)
class Lesion:
    """Disable module ``module`` during ``start <= t < end``.

    - ``silence``: the module is not stepped and all its outputs read 0.
    - ``freeze``: the module is not stepped and its outputs hold their last value.
    """

    id: int
    module: str
    start: float = 0.0
    end: float = math.inf
    mode: str = "silence"

    def active(self, t: float) -> bool:
        return self.start <= t < self.end

    def describe(self) -> dict[str, Any]:
        return {"type": "lesion", **asdict(self)}


Intervention = Clamp | Lesion
