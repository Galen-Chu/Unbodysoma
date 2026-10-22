"""Ready-made organism assemblies."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from .core import Engine, Module
from .interface import Exteroception, Interoception
from .psyche import ActionSelection, Affect, Appraisal, Drives
from .soma import Cardio, Endocrine, Metabolism
from .world import Event, FoodSource, ScriptedWorld


def build_minimal_human(
    events: Iterable[Event] = (),
    seed: int = 0,
    base_dt: float = 0.01,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> Engine:
    """The minimal organism: closed threat and hunger loops of world -> senses -> mind -> body.

    ``overrides`` maps a module name to parameter values, e.g.
    ``{"soma.metabolism": {"initial_reserve": 0.4}}`` (see docs/PARAMETERS.md).
    """
    factories: list[tuple[str, Callable[..., Module], dict[str, Any]]] = [
        (ScriptedWorld.name, ScriptedWorld, {"events": tuple(events)}),
        (FoodSource.name, FoodSource, {}),
        (Exteroception.name, Exteroception, {"seed": seed}),
        (Interoception.name, Interoception, {"seed": seed + 1}),
        (Cardio.name, Cardio, {}),
        (Endocrine.name, Endocrine, {}),
        (Metabolism.name, Metabolism, {}),
        (Appraisal.name, Appraisal, {}),
        (Affect.name, Affect, {}),
        (Drives.name, Drives, {}),
        (ActionSelection.name, ActionSelection, {}),
    ]
    overrides = overrides or {}
    unknown = set(overrides) - {name for name, _, _ in factories}
    if unknown:
        raise ValueError(f"overrides for unknown modules: {sorted(unknown)}")

    engine = Engine(base_dt=base_dt)
    for name, factory, kwargs in factories:
        engine.add(factory(**{**kwargs, **overrides.get(name, {})}))
    return engine
