"""Live viewing with Rerun (https://rerun.io): an optional, read-only observer.

    pip install "unbodysoma[viz]"          # rerun-sdk 0.40.x

    sink = RerunSink(spawn=True).attach(engine)   # opens the Rerun viewer
    sink = RerunSink(save="run.rrd").attach(engine)

Signals are logged as scalar time series under ``signals/<namespace>/<...>``,
engine events (health alerts, interventions) as a text log, and in a grid world
the map: food patches (sized by what is left), water, shelters, hazards and the
organism's position. Written against the rerun-sdk 0.40 API.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..core import BusReader, Engine

_EPS = 1e-9
_LEVELS = {"critical": "ERROR", "warning": "WARN", "info": "INFO"}
GREEN, BLUE, BROWN, RED, WHITE = [60, 180, 75], [0, 130, 200], [170, 110, 40], [230, 25, 75], [240, 240, 240]


def _load_rerun() -> Any:
    try:
        return importlib.import_module("rerun")
    except ImportError as error:
        raise ImportError('Rerun is not installed: pip install "unbodysoma[viz]" (rerun-sdk 0.40.x)') from error


class RerunSink:
    """Streams a run to Rerun. With neither ``spawn`` nor ``save`` it records into memory (``self.memory``)."""

    def __init__(
        self,
        keys: Iterable[str] | None = None,
        every: float = 0.1,
        spawn: bool = False,
        save: str | Path | None = None,
        application_id: str = "unbodysoma",
        module: Any = None,
    ) -> None:
        self.keys = tuple(keys) if keys is not None else None
        self.every = every
        self.spawn = spawn
        self.save = save
        self.application_id = application_id
        self._rr = module  # injectable for tests; imported lazily otherwise
        self._next: float | None = None
        self.memory: Any = None
        self._world: Any = None

    def attach(self, engine: Engine) -> RerunSink:
        rr = self._rr = self._rr or _load_rerun()
        self._rec = rr.RecordingStream(self.application_id)
        if self.spawn:
            self._rec.spawn()
        if self.save is not None:
            self._rec.save(str(self.save))
        if not self.spawn and self.save is None:
            self.memory = self._rec.memory_recording()
        if self.keys is None:
            self.keys = tuple(engine.signals())
        self._paths = {k: "signals/" + k.replace(".", "/") for k in self.keys}
        self._world = next((m for m in engine.modules if m.name == "world.grid"), None)
        if self._world is not None:
            self._log_layout()
        for event in engine.events:
            self._on_event(event)
        engine.observe(self._on_sample)
        engine.on_event(self._on_event)
        return self

    def flush(self) -> None:
        self._rec.flush()

    # -- logging ------------------------------------------------------------

    def _log_layout(self) -> None:
        rr, w = self._rr, self._world
        if w.water:
            self._rec.log(
                "world/water", rr.Points2D([[s.x, s.y] for s in w.water], radii=0.4, colors=[BLUE]), static=True
            )
        if w.shelters:
            positions = [[s.x, s.y] for s in w.shelters]
            self._rec.log(
                "world/shelters",
                rr.Points2D(positions, radii=[s.radius for s in w.shelters], colors=[BROWN]),
                static=True,
            )
        if w.hazards:
            positions = [[h.x, h.y] for h in w.hazards]
            self._rec.log(
                "world/hazards", rr.Points2D(positions, radii=[h.radius for h in w.hazards], colors=[RED]), static=True
            )

    def _on_sample(self, t: float, bus: BusReader) -> None:
        if self._next is None:
            self._next = t
        if t + _EPS < self._next:
            return
        self._next += self.every
        rr = self._rr
        self._rec.set_time("sim_time", duration=t)
        for key, path in self._paths.items():
            if key in bus:
                self._rec.log(path, rr.Scalars(bus.read(key)))
        w = self._world
        if w is not None:
            if w.food:
                radii = [0.1 + 0.4 * a / p.capacity for a, p in zip(w.amounts, w.food, strict=True)]
                self._rec.log("world/food", rr.Points2D([[p.x, p.y] for p in w.food], radii=radii, colors=[GREEN]))
            self._rec.log("world/organism", rr.Points2D([[w.x, w.y]], radii=0.3, colors=[WHITE]))

    def _on_event(self, event: dict[str, Any]) -> None:
        rr = self._rr
        self._rec.set_time("sim_time", duration=float(event["t"]))
        details = ", ".join(f"{k}={v}" for k, v in event.items() if k not in ("t", "kind"))
        level = _LEVELS.get(str(event.get("severity")), "INFO")
        self._rec.log("events", rr.TextLog(f"{event['kind']}: {details}", level=level))
