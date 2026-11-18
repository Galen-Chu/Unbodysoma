"""Energy integration: the reserve as the net glucose balance (Phase 3 closeout).

The store is no longer filled directly by food: eating only delivers oral
glucose to the gut, the positive net flux (total disposal minus production)
is stored, and the metabolic drain and adrenaline's hepatic output are its
costs. Hunger reads the result the other way round — satiety from insulin
(the incretin phase, minutes), acute hunger from a glucose dip, the slow
background from the store. See docs/SOMA.md §2.3.
"""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

RESERVE = "soma.metabolism.energy_reserve"
GLUCOSE = "soma.metabolism.glucose"
INSULIN = "soma.metabolism.insulin"
DEFICIT = "intero.energy_deficit"
EATING = "motor.eating"
KEYS = (RESERVE, GLUCOSE, INSULIN, DEFICIT, EATING)

FOOD_ALWAYS = Event(0.0, 1e9, "world.food_available", 1.0)


def run(events: list[Event], seconds: float, overrides: dict | None = None) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=0, overrides=overrides)
    recorder = Recorder(KEYS, every=10.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, lo: float, hi: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi]


@pytest.fixture(scope="module")
def meal() -> Recorder:
    return run([FOOD_ALWAYS], 4500.0, {"soma.metabolism": {"initial_reserve": 0.4}})


def test_eating_does_not_fill_the_store_directly(meal: Recorder):
    """Storage waits for gut absorption: barely anything moves during the meal."""
    rec = meal
    eating = rec.column(EATING)
    meal_end = max(i for i, e in enumerate(eating) if e > 0.5)
    during = rec.column(RESERVE)[meal_end] - rec.column(RESERVE)[0]
    assert during < 0.02  # the mouthfuls are still in the gut
    assert rec.column(RESERVE)[-1] > rec.column(RESERVE)[0] + 0.1  # ...but the hour after stores the meal
    assert max(rec.column(RESERVE)) > 0.55


def test_insulin_doubles_storage():
    """Mass-action uptake alone stores part of a meal; insulin-mediated disposal
    roughly doubles it — storage flows through the glucose-insulin core."""
    with_insulin = run([FOOD_ALWAYS], 4500.0, {"soma.metabolism": {"initial_reserve": 0.4}})
    without = run([FOOD_ALWAYS], 4500.0, {"soma.metabolism": {"initial_reserve": 0.4, "insulin_action_gain": 1e-6}})
    ate = sum(1 for e in without.column(EATING) if e > 0.5)
    assert ate > 50  # it still ate
    assert max(without.column(RESERVE)) < max(with_insulin.column(RESERVE)) - 0.05


def test_satiety_arrives_with_insulin_within_minutes(meal: Recorder):
    rec = meal
    baseline = mean(window(rec, INSULIN, 0.0, 100.0))
    mid_meal = mean(window(rec, INSULIN, 400.0, 700.0))
    assert mid_meal > baseline + 5.0  # the incretin phase, ahead of absorption
    assert mean(window(rec, DEFICIT, 400.0, 700.0)) < mean(window(rec, DEFICIT, 0.0, 100.0)) - 0.1  # felt


def test_a_glucose_dip_is_felt_as_hunger():
    """The dip channel, isolated: the same clamped hypoglycemia, with the dip
    sensor in place vs moved out of the way."""
    overrides = {"soma.metabolism": {"initial_reserve": 0.5}}
    felt_engine = build_minimal_human([], seed=0, overrides=overrides)
    felt_engine.clamp(GLUCOSE, 65.0, 300.0, 1000.0)
    blind_engine = build_minimal_human(
        [], seed=0, overrides={**overrides, "interface.interoception": {"dip_level": 40.0}}
    )
    blind_engine.clamp(GLUCOSE, 65.0, 300.0, 1000.0)
    felt_rec, blind_rec = Recorder(KEYS, every=10.0), Recorder(KEYS, every=10.0)
    felt_engine.observe(felt_rec)
    felt_engine.run(1200.0)
    blind_engine.observe(blind_rec)
    blind_engine.run(1200.0)
    felt_dip = mean(window(felt_rec, DEFICIT, 500.0, 1000.0))
    blind_dip = mean(window(blind_rec, DEFICIT, 500.0, 1000.0))
    assert felt_dip > blind_dip + 0.3  # the dip itself, on top of the half-empty store


def test_starvation_collapses_glucose():
    """Below the defense threshold the store can no longer defend fasting glucose."""
    rec = run([], 7200.0, {"soma.metabolism": {"initial_reserve": 0.08}})
    assert mean(window(rec, GLUCOSE, 6000.0, 7200.0)) < 75.0  # undefended


def test_fear_mobilizes_the_store():
    """Adrenaline's hepatic output raises glucose and is paid from the reserve (glycogenolysis)."""
    threat = run([Event(300.0, 600.0, "world.threat", 0.9)], 900.0)
    calm = run([], 900.0)
    spent = calm.column(RESERVE)[-1] - threat.column(RESERVE)[-1]
    assert spent > 0.0  # the frightened organism spent store it did not spend at rest
    assert max(window(threat, GLUCOSE, 300.0, 700.0)) > max(window(calm, GLUCOSE, 300.0, 700.0)) + 8.0
