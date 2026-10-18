"""Run records: one self-describing directory per simulation run.

Layout (see docs/OBSERVABILITY.md):

    <run>/meta.json      engine, modules, user config, versions, git commit
    <run>/signals.csv    every declared signal, sampled every ``every`` seconds
    <run>/events.jsonl   engine events: interventions, health alerts, stops
"""

from __future__ import annotations

import csv
import json
import math
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import __version__
from ..core import Engine, SignalBus

_EPS = 1e-9


def _git_revision() -> dict[str, Any] | None:
    cwd = Path(__file__).resolve().parent
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True, timeout=5
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True, timeout=5
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return {"commit": commit, "dirty": bool(status.strip())}


def _jsonable(value: Any) -> Any:
    """JSON has no infinity; open-ended times are written as null."""
    if isinstance(value, float) and math.isinf(value):
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    return value


class RunWriter:
    """Streams a run to disk. Use as a context manager, or call ``close()``."""

    def __init__(self, path: str | Path, every: float = 0.1, config: dict[str, Any] | None = None) -> None:
        self.path = Path(path)
        self.every = every
        self.config = config or {}
        self._engine: Engine | None = None
        self._closed = False
        self._next = 0.0

    def attach(self, engine: Engine) -> RunWriter:
        if self._engine is not None:
            raise RuntimeError("RunWriter is already attached")
        self._engine = engine
        self._keys = engine.signals()
        self.path.mkdir(parents=True, exist_ok=True)
        self._meta = {
            "created": datetime.now(UTC).isoformat(timespec="seconds"),
            "unbodysoma": __version__,
            "python": platform.python_version(),
            "git": _git_revision(),
            "base_dt": engine.base_dt,
            "sample_every": self.every,
            "config": self.config,
            "modules": [
                {
                    "name": m.name,
                    "class": f"{type(m).__module__}.{type(m).__qualname__}",
                    "rate_hz": m.rate_hz,
                    "reads": list(m.reads),
                    "writes": list(m.writes),
                }
                for m in engine.modules
            ],
        }
        self._write_meta()
        self._signals_file = open(self.path / "signals.csv", "w", newline="", encoding="utf-8")
        self._signals = csv.writer(self._signals_file)
        self._signals.writerow(("time", *self._keys))
        self._events_file = open(self.path / "events.jsonl", "w", encoding="utf-8")
        for event in engine.events:  # e.g. interventions scheduled before attaching
            self._on_event(event)
        engine.observe(self._on_sample)
        engine.on_event(self._on_event)
        return self

    def close(self) -> None:
        """Finish the record. The engine may keep running; later ticks are simply not recorded."""
        if self._engine is None or self._closed:
            return
        self._closed = True
        self._signals_file.close()
        self._events_file.close()
        self._meta["end_time"] = self._engine.time
        self._meta["ticks"] = self._engine.tick
        self._write_meta()

    def __enter__(self) -> RunWriter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _write_meta(self) -> None:
        text = json.dumps(_jsonable(self._meta), indent=2, ensure_ascii=False)
        (self.path / "meta.json").write_text(text + "\n", encoding="utf-8")

    def _on_sample(self, t: float, bus: SignalBus) -> None:
        if self._closed:
            return
        if t + _EPS >= self._next:
            self._signals.writerow((t, *(bus.read(k) if k in bus else "" for k in self._keys)))
            self._next += self.every

    def _on_event(self, event: dict[str, Any]) -> None:
        if self._closed:
            return
        self._events_file.write(json.dumps(_jsonable(event), ensure_ascii=False) + "\n")
        self._events_file.flush()


@dataclass
class Run:
    meta: dict[str, Any]
    times: list[float]
    columns: dict[str, list[float | None]]
    events: list[dict[str, Any]]

    def column(self, key: str) -> list[float | None]:
        return self.columns[key]

    def events_of(self, kind: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e["kind"] == kind]


def load_run(path: str | Path) -> Run:
    path = Path(path)
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    with open(path / "signals.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    times = [float(row[0]) for row in rows]
    columns = {key: [float(row[i]) if row[i] != "" else None for row in rows] for i, key in enumerate(header) if i}
    with open(path / "events.jsonl", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]
    return Run(meta, times, columns, events)
