"""Literature-curve validation of the L1 glucose-insulin core (Phase 2).

Structure: Bergman, Ider, Bowden & Cobelli (1979) minimal model; oral input:
two-compartment gut of the Dalla Man, Rizza & Cobelli (2006) meal-model
family. Acceptance bounds: ADA (2021) normal ranges for fasting and 2-h
glucose, plus curve-shape checks (peak magnitude and timing, return to
baseline) and insulin dynamics. See docs/SOMA.md §2.3.

The meal is a 750 s eating window at the default intake rate: 0.225 of the
reserve ≈ 52 g of oral glucose, delivered through the same food_intake
signal the hunger loop uses.
"""

from unbodysoma import build_minimal_human
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

KEYS = ("soma.metabolism.glucose", "soma.metabolism.insulin")
FOOD_ALWAYS = Event(0.0, 1e9, "world.food_available", 1.0)
MEAL_START = 600.0
MEAL_END = 1350.0
TWO_H = MEAL_START + 7200.0
THREE_H = MEAL_START + 10800.0


def run_meal(seed: int = 0) -> Recorder:
    """Fast from 08:00; eat (clamped, ADR-0005) for 750 s from t = 600; run 3.5 h."""
    engine = build_minimal_human([FOOD_ALWAYS], seed=seed)
    engine.clamp("motor.eating", 1.0, MEAL_START, MEAL_END)
    recorder = Recorder(KEYS, every=30.0)
    engine.observe(recorder)
    engine.run(THREE_H + 1800.0)
    return recorder


def at(rec: Recorder, time: float, key: str) -> float:
    times = rec.times()
    return rec.column(key)[min(range(len(times)), key=lambda i: abs(times[i] - time))]


def test_fasting_glucose_is_in_the_normal_range():
    rec = run_meal()
    fasting = [v for t, v in zip(rec.times(), rec.column("soma.metabolism.glucose"), strict=True) if t < MEAL_START]
    assert 70.0 <= min(fasting) and max(fasting) <= 99.0  # ADA (2021) normal fasting


def test_oral_glucose_peak_magnitude_and_timing():
    rec = run_meal()
    glucose = rec.column("soma.metabolism.glucose")
    times = rec.times()
    peak_i = max(range(len(glucose)), key=lambda i: glucose[i])
    assert 110.0 < glucose[peak_i] < 190.0  # healthy meal response, below the diabetic ceiling
    peak_min = (times[peak_i] - MEAL_START) / 60.0
    assert 20.0 <= peak_min <= 60.0  # literature: oral glucose peaks at 30–60 min


def test_two_hour_glucose_meets_the_ada_criterion():
    rec = run_meal()
    assert at(rec, TWO_H, "soma.metabolism.glucose") < 140.0  # ADA (2021) 2-h normal
    assert at(rec, THREE_H, "soma.metabolism.glucose") < 140.0


def test_glucose_returns_toward_fasting():
    rec = run_meal()
    fasting = at(rec, 300.0, "soma.metabolism.glucose")
    late = at(rec, THREE_H + 1800.0, "soma.metabolism.glucose")  # 4 h after the meal
    assert abs(late - fasting) <= 15.0


def test_insulin_rises_with_the_meal_and_returns_to_basal():
    rec = run_meal()
    insulin = rec.column("soma.metabolism.insulin")
    basal = at(rec, 300.0, "soma.metabolism.insulin")
    assert 5.0 <= basal <= 12.0  # typical fasting 5–15 μU/mL
    peak = max(insulin)
    assert 3.0 * basal <= peak <= 120.0  # a real post-meal surge, within physiological range
    assert at(rec, THREE_H, "soma.metabolism.insulin") < 2.0 * basal


def test_sustained_threat_mobilizes_glucose():
    engine = build_minimal_human([Event(0.0, 1e9, "world.threat", 0.9)], seed=0)
    recorder = Recorder(KEYS, every=60.0)
    engine.observe(recorder)
    engine.run(3600.0)
    glucose = recorder.column("soma.metabolism.glucose")
    assert max(glucose) - glucose[0] >= 15.0  # adrenergic glycogenolysis, as in the L0 model
    assert max(glucose) <= 180.0


def test_meal_curve_is_deterministic_for_a_seed():
    a = run_meal(seed=3).column("soma.metabolism.glucose")
    b = run_meal(seed=3).column("soma.metabolism.glucose")
    assert a == b


def test_starvation_still_undefends_glucose():
    """Hypoglycemia develops on the L1 timescale: the second hour, not the first.

    The defended fasting level collapses with the reserve; glucose follows at
    the glucose-effectiveness time constant (~40 min), as the minimal model
    implies — the old 1-hour collapse was an L0 tracking artifact.
    """
    engine = build_minimal_human([], seed=0, overrides={"soma.metabolism": {"initial_reserve": 0.08}})
    recorder = Recorder(KEYS, every=10.0)
    engine.observe(recorder)
    engine.run(7200.0)
    assert min(recorder.column("soma.metabolism.glucose")) < 50.0
