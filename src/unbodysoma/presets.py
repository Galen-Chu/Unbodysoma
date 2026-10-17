"""Ready-made organism assemblies."""

from __future__ import annotations

from collections.abc import Iterable

from .core import Engine
from .interface import Exteroception, Interoception
from .psyche import ActionSelection, Affect, Appraisal, Drives
from .soma import Cardio, Endocrine, Metabolism
from .world import Event, ScriptedWorld


def build_minimal_human(events: Iterable[Event] = (), seed: int = 0, base_dt: float = 0.01) -> Engine:
    """The Phase 0 organism: one closed loop of world -> senses -> mind -> body -> senses."""
    engine = Engine(base_dt=base_dt)
    for module in (
        ScriptedWorld(events),
        Exteroception(seed=seed),
        Interoception(seed=seed + 1),
        Cardio(),
        Endocrine(),
        Metabolism(),
        Appraisal(),
        Affect(),
        Drives(),
        ActionSelection(),
    ):
        engine.add(module)
    return engine
