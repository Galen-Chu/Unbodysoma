"""Saving snapshots to disk and loading them back. See docs/adr/0004-explicit-module-state.md.

Module state can hold values JSON cannot represent directly: random generators,
tuples (``random.getstate()`` returns nested tuples) and non-finite floats. They are
written as tagged objects, so the file is strict JSON and round-trips exactly.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from .engine import Snapshot

FORMAT = "unbodysoma.snapshot/1"


def encode(value: Any) -> Any:
    if isinstance(value, random.Random):
        return {"__random__": encode(value.getstate())}
    if isinstance(value, tuple):
        return {"__tuple__": [encode(v) for v in value]}
    if isinstance(value, float) and not math.isfinite(value):
        return {"__float__": repr(value)}
    if isinstance(value, dict):
        if any(k.startswith("__") and k.endswith("__") for k in value):
            raise ValueError("state dictionaries must not use reserved __tag__ keys")
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if value is None or isinstance(value, bool | int | float | str):
        return value
    raise TypeError(f"cannot save module state of type {type(value).__name__}")


def decode(value: Any) -> Any:
    if isinstance(value, dict):
        if "__random__" in value:
            rng = random.Random()
            rng.setstate(decode(value["__random__"]))
            return rng
        if "__tuple__" in value:
            return tuple(decode(v) for v in value["__tuple__"])
        if "__float__" in value:
            return float(value["__float__"])
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def save_snapshot(snapshot: Snapshot, path: str | Path) -> None:
    data = {
        "format": FORMAT,
        "tick": snapshot.tick,
        "signals": encode(snapshot.signals),
        "modules": encode(snapshot.modules),
        "active_interventions": sorted(snapshot.active_interventions),
    }
    Path(path).write_text(json.dumps(data, allow_nan=False) + "\n", encoding="utf-8")


def load_snapshot(path: str | Path) -> Snapshot:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != FORMAT:
        raise ValueError(f"{path}: not a snapshot file (expected format {FORMAT!r})")
    return Snapshot(
        tick=int(data["tick"]),
        signals=decode(data["signals"]),
        modules=decode(data["modules"]),
        active_interventions=frozenset(data["active_interventions"]),
    )
