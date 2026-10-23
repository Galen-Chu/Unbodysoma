"""Ready-made organism assemblies."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from .core import Engine, Module
from .interface import Exteroception, Interoception
from .interface.exteroception import SPATIAL_CHANNELS
from .psyche import ActionSelection, Affect, Appraisal, Drives, Navigation
from .soma import Cardio, Circadian, Endocrine, Metabolism, SleepHomeostat
from .world import Event, FoodPatch, FoodSource, GridWorld, Hazard, ScriptedWorld

Factory = tuple[str, Callable[..., Module], dict[str, Any]]
Overrides = Mapping[str, Mapping[str, Any]]


def _body_and_mind(seed: int) -> list[Factory]:
    """Everything except the world: shared by all presets, with one seed offset per random stream."""
    return [
        (Interoception.name, Interoception, {"seed": seed + 1}),
        (Circadian.name, Circadian, {}),
        (SleepHomeostat.name, SleepHomeostat, {}),
        (Cardio.name, Cardio, {"seed": seed + 2}),
        (Endocrine.name, Endocrine, {}),
        (Metabolism.name, Metabolism, {}),
        (Appraisal.name, Appraisal, {}),
        (Affect.name, Affect, {"seed": seed + 3}),
        (Drives.name, Drives, {}),
        (ActionSelection.name, ActionSelection, {"seed": seed + 4}),
    ]


def _assemble(factories: list[Factory], base_dt: float, overrides: Overrides | None) -> Engine:
    overrides = overrides or {}
    unknown = set(overrides) - {name for name, _, _ in factories}
    if unknown:
        raise ValueError(f"overrides for unknown modules: {sorted(unknown)}")
    engine = Engine(base_dt=base_dt)
    for name, factory, kwargs in factories:
        engine.add(factory(**{**kwargs, **overrides.get(name, {})}))
    return engine


def build_minimal_human(
    events: Iterable[Event] = (),
    seed: int = 0,
    base_dt: float = 0.01,
    overrides: Overrides | None = None,
) -> Engine:
    """The minimal organism in a scripted world: closed threat, hunger and sleep loops.

    ``overrides`` maps a module name to parameter values, e.g.
    ``{"soma.metabolism": {"initial_reserve": 0.4}}`` (see docs/PARAMETERS.md).
    """
    factories: list[Factory] = [
        (ScriptedWorld.name, ScriptedWorld, {"events": tuple(events)}),
        (FoodSource.name, FoodSource, {}),
        (Exteroception.name, Exteroception, {"seed": seed}),
        *_body_and_mind(seed),
    ]
    return _assemble(factories, base_dt, overrides)


DEFAULT_FOOD = (
    FoodPatch(4.0, 4.0),
    FoodPatch(16.0, 5.0),
    FoodPatch(15.0, 16.0),
    FoodPatch(5.0, 15.0),
)
DEFAULT_HAZARDS = (Hazard(13.0, 13.0, radius=3.0),)  # guards the patch at (15, 16)


def build_grid_human(
    food: Iterable[FoodPatch] = DEFAULT_FOOD,
    hazards: Iterable[Hazard] = DEFAULT_HAZARDS,
    width: float = 20.0,
    height: float = 20.0,
    start: tuple[float, float] = (10.0, 10.0),
    seed: int = 0,
    base_dt: float = 0.05,
    overrides: Overrides | None = None,
) -> Engine:
    """The same organism living in a 2D grid world: it has to find food, avoid hazards and move."""
    world = {"width": width, "height": height, "food": tuple(food), "hazards": tuple(hazards), "start": start}
    factories: list[Factory] = [
        (GridWorld.name, GridWorld, world),
        (FoodSource.name, FoodSource, {}),
        (Exteroception.name, Exteroception, {"seed": seed, "channels": SPATIAL_CHANNELS}),
        *_body_and_mind(seed),
        (Navigation.name, Navigation, {"seed": seed + 5}),
    ]
    return _assemble(factories, base_dt, overrides)
