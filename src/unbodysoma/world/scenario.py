"""Scripted environments: timelines of stimuli applied to the organism."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..core import BusPort, Module

DEFAULT_WORLD_SIGNALS = ("world.threat", "world.food_intake")


@dataclass(frozen=True)
class Event:
    """Adds ``value`` to signal ``key`` during ``start <= t < end`` (seconds)."""

    start: float
    end: float
    key: str
    value: float


class ScriptedWorld(Module):
    name = "world.scripted"
    rate_hz = 10.0

    def __init__(self, events: Iterable[Event] = (), signals: Iterable[str] = DEFAULT_WORLD_SIGNALS) -> None:
        self.events = tuple(events)
        self.writes = tuple(sorted(set(signals) | {e.key for e in self.events}))

    def setup(self, port: BusPort) -> None:
        for key in self.writes:
            port.write(key, 0.0)

    def step(self, dt: float, port: BusPort) -> None:
        t = port.time
        for key in self.writes:
            port.write(key, sum(e.value for e in self.events if e.key == key and e.start <= t < e.end))
