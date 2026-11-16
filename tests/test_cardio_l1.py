"""Literature-curve validation of the L1 heart-rate kinetics (Phase 2).

Anchors: Whipp & Wasserman (1972) for exercise on-kinetics (the fundamental
component rises with a time constant of tens of seconds — not instantly, and
not all of it fast), Tanaka, Monahan & Seals (2001) for the age-scaled
maximal rate (208 − 0.7 × age), and Cole et al. (1999) for heart-rate
recovery (a healthy adult drops ≥ 12 bpm in the first minute after exercise).
See docs/SOMA.md §2.1.

Exercise protocol: motor.exertion is clamped to 0.7 for six minutes; the
fast adrenergic path is covered by the existing fear-response suite.
"""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

HR = "soma.cardio.heart_rate"
ONSET = 600.0
END = 960.0  # six minutes of moderate exercise


def run_exercise(
    overrides: dict | None = None,
    seconds: float = 1200.0,
    events: tuple[Event, ...] = (),
    exertion: float = 0.7,
) -> Recorder:
    engine: Engine = build_minimal_human(list(events), seed=0, overrides=overrides)
    engine.clamp("motor.exertion", exertion, ONSET, END)
    recorder = Recorder((HR,), every=1.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def smoothed(rec: Recorder, time: float, width: float = 5.0) -> float:
    return mean(v for t, v in zip(rec.times(), rec.column(HR), strict=True) if time - width <= t <= time + width)


@pytest.fixture(scope="module")
def exercise() -> Recorder:
    return run_exercise()


def test_resting_and_steady_levels_are_unchanged(exercise: Recorder):
    rec = exercise
    base = mean(v for t, v in zip(rec.times(), rec.column(HR), strict=True) if 500.0 <= t < ONSET)
    steady = mean(v for t, v in zip(rec.times(), rec.column(HR), strict=True) if ONSET + 240.0 <= t < END)
    assert 60.0 <= base <= 70.0
    assert steady - base == pytest.approx(70.0 * 0.7, abs=3.0)  # the L0 steady-state gain is preserved


def test_exercise_onset_is_graded_not_instant(exercise: Recorder):
    rec = exercise
    base = smoothed(rec, ONSET - 60.0, width=30.0)
    steady = smoothed(rec, END - 60.0, width=30.0)
    rise = steady - base
    frac15 = (smoothed(rec, ONSET + 15.0) - base) / rise
    assert 0.30 <= frac15 <= 0.62  # fast phase covers the first jump, but not everything
    t63 = next(m for m in range(15, 120) if smoothed(rec, ONSET + m) - base >= 0.63 * rise)
    assert 15 <= t63 <= 45  # Whipp & Wasserman: τ of tens of seconds


def test_recovery_meets_the_cole_criterion(exercise: Recorder):
    rec = exercise
    end = smoothed(rec, END - 10.0)
    after_one_minute = smoothed(rec, END + 60.0)
    assert end - after_one_minute >= 12.0  # Cole et al.: ≥ 12 bpm in the first minute


def test_maximal_rate_scales_with_age():
    events = (Event(0.0, 1200.0, "world.threat", 1.0),)
    young = run_exercise({"soma.cardio": {"age_years": 25.0}}, 1200.0, events, exertion=1.0)
    old = run_exercise({"soma.cardio": {"age_years": 80.0}}, 1200.0, events, exertion=1.0)
    assert max(old.column(HR)) <= 152.0 + 3.0  # Tanaka: 208 − 0.7 × 80
    assert max(young.column(HR)) > max(old.column(HR)) + 15.0
