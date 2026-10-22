"""Acceptance tests for the closed hunger loop: food -> senses -> hunger -> eating -> intake -> reserve."""

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import HealthMonitor, Recorder
from unbodysoma.world import Event

FOOD_ALWAYS = Event(0.0, 1e9, "world.food_available", 1.0)
KEYS = (
    "psyche.drive.hunger",
    "motor.eating",
    "motor.exertion",
    "soma.metabolism.energy_reserve",
    "soma.metabolism.glucose",
    "psyche.affect.valence",
)


def hungry(events, reserve: float = 0.4, seed: int = 0) -> Engine:
    return build_minimal_human(events, seed=seed, overrides={"soma.metabolism": {"initial_reserve": reserve}})


def record(engine: Engine, seconds: float, every: float = 1.0) -> Recorder:
    recorder = Recorder(KEYS, every=every)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, start: float, end: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if start <= t < end]


def test_hungry_organism_eats_until_sated():
    rec = record(hungry([FOOD_ALWAYS]), 2000.0)
    reserve = rec.column("soma.metabolism.energy_reserve")
    assert max(window(rec, "motor.eating", 0, 200)) == 1.0  # starts eating once hunger builds
    assert reserve[-1] > 0.7 > reserve[0]  # the meal refilled the reserve
    eating = rec.column("motor.eating")
    first, last = eating.index(1.0), max(i for i, e in enumerate(eating) if e == 1.0)
    assert all(eating[first : last + 1])  # one continuous meal...
    assert eating[-1] == 0.0  # ...that stopped when sated
    # Afterwards hunger creeps back up only slightly: far below the level that starts another meal.
    assert max(rec.column("psyche.drive.hunger")[last + 1 :]) < 0.2
    assert rec.column("psyche.affect.valence")[-1] > rec.column("psyche.affect.valence")[100]


def test_no_food_means_no_eating():
    rec = record(hungry([]), 600.0)
    assert max(rec.column("motor.eating")) == 0.0
    reserve = rec.column("soma.metabolism.energy_reserve")
    assert reserve[-1] < reserve[0]


def test_sated_organism_ignores_food():
    rec = record(build_minimal_human([FOOD_ALWAYS]), 600.0)  # default reserve 0.8: not hungry
    assert max(rec.column("motor.eating")) == 0.0


def test_threat_interrupts_a_meal_which_then_resumes():
    events = [FOOD_ALWAYS, Event(400.0, 430.0, "world.threat", 0.9)]
    rec = record(hungry(events), 700.0, every=0.5)
    assert min(window(rec, "motor.eating", 300, 400)) == 1.0  # mid-meal
    assert max(window(rec, "motor.eating", 402, 430)) == 0.0  # dropped the food...
    assert max(window(rec, "motor.exertion", 402, 430)) > 0.5  # ...and ran
    assert max(window(rec, "motor.eating", 440, 700)) == 1.0  # back to eating, still hungry


def test_starvation_is_flagged_by_the_health_monitor():
    engine = hungry([], reserve=0.08)
    monitor = HealthMonitor().attach(engine)
    rec = record(engine, 3600.0, every=10.0)
    raised = {a.rule for a in monitor.alerts if a.raised}
    assert {"starvation", "glucose_abnormal"} <= raised
    assert monitor.worst == "warning"  # unhealthy, but no model bug
    assert min(rec.column("soma.metabolism.glucose")) < 50.0


def test_intake_requires_both_food_and_eating():
    engine = hungry([Event(0.0, 1e9, "world.food_available", 1.0)])
    engine.clamp("motor.eating", 0.0)  # food is there, but the organism is prevented from eating
    rec = record(engine, 600.0)
    reserve = rec.column("soma.metabolism.energy_reserve")
    assert reserve[-1] < reserve[0]


def test_unknown_override_is_rejected():
    with pytest.raises(ValueError, match="unknown modules"):
        build_minimal_human(overrides={"soma.liver": {}})
