"""Declarative specifications of module parameters and output signals.

Specs are the single source of truth for units, valid ranges, descriptions and
provenance. The engine validates against them, run records store them, health
rules and docs/SIGNALS.md / docs/PARAMETERS.md are generated from them.
See docs/adr/0006-declarative-parameter-and-signal-specs.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SignalSpec:
    """What a signal means: unit, valid range and a one-line description."""

    key: str
    unit: str
    lo: float = -math.inf
    hi: float = math.inf
    description: str = ""


@dataclass(frozen=True)
class ParamSpec:
    """A tunable model parameter: default, unit, valid range and where the value comes from."""

    name: str
    default: float
    unit: str = ""
    lo: float = -math.inf
    hi: float = math.inf
    description: str = ""
    source: str = "L0 toy value"

    def check(self, value: Any, owner: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"{owner}.{self.name} must be a number, got {value!r}")
        if not self.lo <= value <= self.hi:
            raise ValueError(f"{owner}.{self.name} = {value!r} outside [{self.lo:g}, {self.hi:g}]")
