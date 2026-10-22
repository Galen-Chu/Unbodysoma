"""Acceptance tests for ADR-0004: the whole simulation can be snapshotted and restored."""

import copy
import random

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.world import Event

THREAT = [Event(60.0, 90.0, "world.threat", 0.9)]


def trajectory(engine: Engine, seconds: float) -> list[dict[str, float]]:
    states = []
    for _ in range(round(seconds / engine.base_dt)):
        engine.step()
        states.append(engine.bus.snapshot())
    return states


def comparable(value):
    """``random.Random`` compares by identity, so compare its internal state instead (recursively)."""
    if isinstance(value, random.Random):
        return value.getstate()
    if isinstance(value, dict):
        return {k: comparable(v) for k, v in value.items()}
    return value


def test_restore_reproduces_the_future_exactly():
    engine = build_minimal_human(THREAT, seed=3)
    engine.run(75.0)  # mid-threat: the organism is fleeing, hormones are high
    snap = engine.snapshot()
    first = trajectory(engine, 60.0)
    engine.restore(snap)
    second = trajectory(engine, 60.0)
    assert first == second


def test_snapshot_path_matches_uninterrupted_run():
    straight = build_minimal_human(THREAT, seed=3)
    straight.run(135.0)

    branched = build_minimal_human(THREAT, seed=3)
    branched.run(75.0)
    snap = branched.snapshot()
    branched.run(30.0)  # wander off, then rewind
    branched.restore(snap)
    branched.run(60.0)

    assert branched.tick == straight.tick
    assert branched.bus.snapshot() == straight.bus.snapshot()


def test_snapshot_can_be_restored_repeatedly():
    engine = build_minimal_human(THREAT, seed=0)
    engine.run(70.0)
    snap = engine.snapshot()
    outcomes = []
    for _ in range(3):
        engine.restore(snap)
        engine.run(10.0)
        outcomes.append(engine.bus.snapshot())
    assert outcomes[0] == outcomes[1] == outcomes[2]


def test_every_mutable_attribute_is_covered_by_module_state():
    """Guards against a module forgetting to declare a state field."""
    engine = build_minimal_human(THREAT, seed=0)
    engine.run(70.0)
    snap = engine.snapshot()
    before = {m.name: comparable(copy.deepcopy(vars(m))) for m in engine.modules}
    engine.run(40.0)
    engine.restore(snap)
    after = {m.name: comparable(vars(m)) for m in engine.modules}
    for name in before:
        assert after[name] == before[name], name


def test_restore_rejects_snapshot_from_a_different_assembly():
    snap = build_minimal_human().snapshot()
    other = Engine()
    with pytest.raises(ValueError, match="different modules"):
        other.restore(snap)
