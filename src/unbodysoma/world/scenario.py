"""Scripted environments: timelines of stimuli applied to the organism."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from ..core import BusPort, Module, SignalSpec

DEFAULT_WORLD_SIGNALS = (
    "world.threat",
    "world.food_available",
    "world.water_available",
    "world.in_shelter",
    "world.shelter_known",
    "world.ambient_temperature",
)
DEFAULT_BASELINES = {"world.ambient_temperature": 22.0}

WORLD_SIGNAL_SPECS = (
    SignalSpec("world.threat", "normalized", 0.0, 1.0, "Objective threat present in the environment"),
    SignalSpec("world.food_available", "normalized", 0.0, 1.0, "Food within reach (1 = plenty)"),
    SignalSpec("world.water_available", "normalized", 0.0, 1.0, "Water within reach"),
    SignalSpec("world.in_shelter", "indicator", 0.0, 1.0, "1 inside a shelter"),
    SignalSpec("world.shelter_known", "indicator", 0.0, 1.0, "1 if the world has a shelter"),
    SignalSpec("world.ambient_temperature", "°C", -60.0, 60.0, "Temperature where the organism is"),
)


@dataclass(frozen=True)
class Event:
    """Adds ``value`` to signal ``key`` during ``start <= t < end`` (seconds), on top of its baseline."""

    start: float
    end: float
    key: str
    value: float


class ScriptedWorld(Module):
    name = "world.scripted"
    rate_hz = 10.0
    config_args = ("events", "signals", "baselines")

    def __init__(
        self,
        events: Iterable[Event] = (),
        signals: Iterable[str] = DEFAULT_WORLD_SIGNALS,
        baselines: Mapping[str, float] | None = None,
    ) -> None:
        self.events = tuple(events)
        self.signals = tuple(signals)
        self.baselines = dict(DEFAULT_BASELINES if baselines is None else baselines)
        self.writes = tuple(sorted(set(signals) | {e.key for e in self.events}))
        self.signal_specs = tuple(s for s in WORLD_SIGNAL_SPECS if s.key in self.writes)

    def get_params(self) -> dict[str, Any]:
        return {"events": [asdict(e) for e in self.events], "signals": list(self.signals), "baselines": self.baselines}

    def setup(self, port: BusPort) -> None:
        for key in self.writes:
            port.write(key, self.baselines.get(key, 0.0))

    def step(self, dt: float, port: BusPort) -> None:
        t = port.time
        for key in self.writes:
            active = sum(e.value for e in self.events if e.key == key and e.start <= t < e.end)
            port.write(key, self.baselines.get(key, 0.0) + active)
