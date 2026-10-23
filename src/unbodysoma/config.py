"""Scenario files: describe an experiment in TOML instead of Python.

See docs/SCENARIOS.md for the format and docs/adr/0008-toml-scenario-files.md for
the design. Unknown keys are errors, reported with their location, because a
silently ignored typo in an experiment definition is worse than a crash.
"""

from __future__ import annotations

import hashlib
import math
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import Engine
from .observe import HealthMonitor, RunWriter
from .presets import build_grid_human, build_minimal_human
from .world import Event, FoodPatch, Hazard


class ScenarioError(ValueError):
    """A scenario file does not follow the format."""


_TOP = {"scenario", "organism", "events", "world", "interventions", "observe"}
_SCENARIO = {"name", "description", "duration_s", "duration_h", "seed", "base_dt"}
_ORGANISM = {"preset", "overrides"}
_EVENT = {"start", "end", "key", "value"}
_WORLD = {"width", "height", "start", "food", "hazards"}
_FOOD = {"x", "y", "capacity", "regrow_per_hour"}
_HAZARD = {"x", "y", "radius", "strength", "start", "end", "every"}
_CLAMP = {"type", "key", "value", "start", "end"}
_LESION = {"type", "module", "start", "end", "mode"}
_OBSERVE = {"record_every", "monitor", "monitor_every", "halt_on"}
PRESETS: dict[str, Callable[..., Engine]] = {"minimal": build_minimal_human, "grid": build_grid_human}


def _table(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioError(f"{where}: expected a table, got {type(value).__name__}")
    return value


def _keys(table: Mapping[str, Any], allowed: set[str], where: str, required: Iterable[str] = ()) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ScenarioError(f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")
    missing = sorted(set(required) - set(table))
    if missing:
        raise ScenarioError(f"{where}: missing required key(s) {missing}")


def _number(table: Mapping[str, Any], key: str, where: str, default: float | None = None) -> float:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ScenarioError(f"{where}.{key}: expected a number, got {value!r}")
    return float(value)


def _records(value: Any, where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise ScenarioError(f"{where}: expected an array of tables ([[{where}]])")
    return value


@dataclass
class Scenario:
    name: str
    preset: str
    duration_s: float
    seed: int = 0
    description: str = ""
    base_dt: float | None = None
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    world: dict[str, Any] = field(default_factory=dict)
    interventions: list[dict[str, Any]] = field(default_factory=list)
    record_every: float = 1.0
    monitor: bool = True
    monitor_every: float = 1.0
    halt_on: str | None = "critical"
    source: str = ""  # the TOML text, stored in run records

    # -- building -----------------------------------------------------------

    def build(self) -> Engine:
        kwargs: dict[str, Any] = {"seed": self.seed, "overrides": self.overrides}
        if self.base_dt is not None:
            kwargs["base_dt"] = self.base_dt
        if self.preset == "minimal":
            kwargs["events"] = self.events
        else:
            kwargs.update(self.world)
        try:
            engine = PRESETS[self.preset](**kwargs)
        except (TypeError, ValueError) as error:  # e.g. an override naming an unknown parameter
            raise ScenarioError(f"organism: {error}") from error
        for i, iv in enumerate(self.interventions):
            try:
                if iv["type"] == "clamp":
                    engine.clamp(iv["key"], iv["value"], iv["start"], iv["end"])
                else:
                    engine.lesion(iv["module"], iv["start"], iv["end"], iv["mode"])
            except ValueError as error:
                raise ScenarioError(f"interventions[{i}]: {error}") from error
        return engine

    def run(self, out: str | Path | None = None) -> RunResult:
        engine = self.build()
        monitor = HealthMonitor(every=self.monitor_every, halt_on=self.halt_on).attach(engine) if self.monitor else None
        writer = None
        if out is not None:
            config = {"scenario": self.name, "seed": self.seed, "source_sha256": _sha256(self.source)}
            writer = RunWriter(out, every=self.record_every, config={**config, "source": self.source}).attach(engine)
        try:
            stopped = engine.run(self.duration_s)
        finally:
            if writer is not None:
                writer.close()
        return RunResult(self, engine, monitor, stopped)


@dataclass
class RunResult:
    scenario: Scenario
    engine: Engine
    monitor: HealthMonitor | None
    stopped: str | None

    def summary(self) -> str:
        e = self.engine
        status = f"stopped: {self.stopped}" if self.stopped else "completed"
        lines = [
            f"scenario   {self.scenario.name} (preset {self.scenario.preset}, seed {self.scenario.seed})",
            f"simulated  {e.time:.1f} s ({e.time / 3600:.2f} h), {status}",
        ]
        if self.monitor is not None:
            raised = [a for a in self.monitor.alerts if a.raised]
            lines.append(
                f"alerts     {len(raised)}" + "".join(f"\n  t={a.t:.0f}s {a.severity}: {a.message}" for a in raised)
            )
        return "\n".join(lines)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -- parsing --------------------------------------------------------------------


def parse_scenario(text: str, name: str = "scenario") -> Scenario:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ScenarioError(f"not valid TOML: {error}") from error
    _keys(data, _TOP, "(top level)", required={"scenario", "organism"})

    meta = _table(data["scenario"], "scenario")
    _keys(meta, _SCENARIO, "scenario")
    if ("duration_s" in meta) == ("duration_h" in meta):
        raise ScenarioError("scenario: give exactly one of duration_s or duration_h")
    duration = (
        _number(meta, "duration_s", "scenario")
        if "duration_s" in meta
        else 3600 * _number(meta, "duration_h", "scenario")
    )
    seed = meta.get("seed", 0)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ScenarioError(f"scenario.seed: expected a non-negative integer, got {seed!r}")

    organism = _table(data["organism"], "organism")
    _keys(organism, _ORGANISM, "organism", required={"preset"})
    preset = organism["preset"]
    if preset not in PRESETS:
        raise ScenarioError(f"organism.preset: {preset!r} is not one of {sorted(PRESETS)}")
    overrides = {
        k: dict(_table(v, f"organism.overrides.{k}"))
        for k, v in _table(organism.get("overrides", {}), "organism.overrides").items()
    }

    scenario = Scenario(
        name=str(meta.get("name", name)),
        preset=preset,
        duration_s=duration,
        seed=seed,
        description=str(meta.get("description", "")),
        base_dt=_number(meta, "base_dt", "scenario") if "base_dt" in meta else None,
        overrides=overrides,
        source=text,
    )

    if "events" in data:
        if preset != "minimal":
            raise ScenarioError("events: scripted events are only available with preset = 'minimal'")
        for i, ev in enumerate(_records(data["events"], "events")):
            where = f"events[{i}]"
            _keys(ev, _EVENT, where, required=_EVENT)
            scenario.events.append(
                Event(
                    _number(ev, "start", where), _number(ev, "end", where), str(ev["key"]), _number(ev, "value", where)
                )
            )

    if "world" in data:
        if preset != "grid":
            raise ScenarioError("world: a world layout is only available with preset = 'grid'")
        world = _table(data["world"], "world")
        _keys(world, _WORLD, "world")
        layout: dict[str, Any] = {}
        for key in ("width", "height"):
            if key in world:
                layout[key] = _number(world, key, "world")
        if "start" in world:
            start = world["start"]
            if not (isinstance(start, list) and len(start) == 2):
                raise ScenarioError("world.start: expected [x, y]")
            layout["start"] = (float(start[0]), float(start[1]))
        if "food" in world:
            food = []
            for i, f in enumerate(_records(world["food"], "world.food")):
                where = f"world.food[{i}]"
                _keys(f, _FOOD, where, required={"x", "y"})
                food.append(FoodPatch(**{k: _number(f, k, where) for k in f}))
            layout["food"] = food
        if "hazards" in world:
            hazards = []
            for i, h in enumerate(_records(world["hazards"], "world.hazards")):
                where = f"world.hazards[{i}]"
                _keys(h, _HAZARD, where, required={"x", "y"})
                hazards.append(Hazard(**{k: _number(h, k, where) for k in h}))
            layout["hazards"] = hazards
        scenario.world = layout

    for i, iv in enumerate(_records(data.get("interventions", []), "interventions")):
        where = f"interventions[{i}]"
        kind = iv.get("type")
        if kind == "clamp":
            _keys(iv, _CLAMP, where, required={"type", "key", "value"})
            entry = {"type": "clamp", "key": str(iv["key"]), "value": _number(iv, "value", where)}
        elif kind == "lesion":
            _keys(iv, _LESION, where, required={"type", "module"})
            entry = {"type": "lesion", "module": str(iv["module"]), "mode": str(iv.get("mode", "silence"))}
        else:
            raise ScenarioError(f"{where}.type: expected 'clamp' or 'lesion', got {kind!r}")
        entry["start"] = _number(iv, "start", where, 0.0)
        entry["end"] = _number(iv, "end", where, math.inf)
        scenario.interventions.append(entry)

    if "observe" in data:
        observe = _table(data["observe"], "observe")
        _keys(observe, _OBSERVE, "observe")
        scenario.record_every = _number(observe, "record_every", "observe", 1.0)
        scenario.monitor_every = _number(observe, "monitor_every", "observe", 1.0)
        monitor = observe.get("monitor", True)
        if not isinstance(monitor, bool):
            raise ScenarioError(f"observe.monitor: expected true or false, got {monitor!r}")
        scenario.monitor = monitor
        halt_on = observe.get("halt_on", "critical")
        if halt_on not in ("info", "warning", "critical", "none"):
            raise ScenarioError(f"observe.halt_on: expected 'info', 'warning', 'critical' or 'none', got {halt_on!r}")
        scenario.halt_on = None if halt_on == "none" else halt_on

    scenario.build()  # catch semantic errors (unknown modules, parameters, signals) at load time
    return scenario


def load_scenario(path: str | Path) -> Scenario:
    path = Path(path)
    return parse_scenario(path.read_text(encoding="utf-8"), name=path.stem)
