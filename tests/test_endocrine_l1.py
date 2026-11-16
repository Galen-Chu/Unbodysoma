"""Literature-curve validation of the L1 HPA axis (Phase 2).

Anchors: Dickerson & Kemeny (2004) for the acute stress cortisol response —
little movement in the first few minutes, a peak 20–40 min after onset at
+50–90% of baseline, recovery within 1–2 h — and Clow, Hucklebridge, Stalder,
Evans & Thorn (2010) for the cortisol awakening response: +50–75% over the
30–45 min after waking. See docs/SOMA.md §2.2.
"""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

pytestmark = pytest.mark.slow  # the awakening test simulates a day and a half

HOUR = 3600.0
FOOD = Event(0.0, 1e9, "world.food_available", 1.0)
WATER = Event(0.0, 1e9, "world.water_available", 1.0)
CORTISOL = "soma.endocrine.cortisol"
KEYS = (CORTISOL, "motor.sleeping")
ONSET = 3600.0  # 09:00
OFFSET = 5400.0  # a 30-min stressor, as in laboratory paradigms


def run_stress(events: list[Event], seconds: float, seed: int = 0, every: float = 30.0) -> Recorder:
    engine = build_minimal_human(events, seed=seed)
    recorder = Recorder((CORTISOL,), every=every)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def at(rec: Recorder, time: float) -> float:
    times = rec.times()
    return rec.column(CORTISOL)[min(range(len(times)), key=lambda i: abs(times[i] - time))]


def test_acute_stress_response_is_delayed_and_peaks_in_the_window():
    rec = run_stress([Event(ONSET, OFFSET, "world.threat", 0.9)], 14400.0)
    cortisol = rec.column(CORTISOL)
    times = rec.times()
    base = at(rec, ONSET - 600.0)
    rise = max(cortisol) - base
    assert (at(rec, ONSET + 180.0) - base) < 0.3 * rise  # barely moved at 3 min
    peak_min = (times[cortisol.index(max(cortisol))] - ONSET) / 60.0
    assert 15.0 <= peak_min <= 45.0  # Dickerson & Kemeny: 20–40 min
    assert 0.4 * base <= rise <= 1.0 * base  # +40–100% of baseline


def test_cortisol_recovers_within_two_hours():
    """Same seed with and without the stressor: the difference decays back."""
    stressed = run_stress([Event(ONSET, OFFSET, "world.threat", 0.9)], 14400.0)
    control = run_stress([], 14400.0)
    assert abs(at(stressed, OFFSET + 60 * 60) - at(control, OFFSET + 60 * 60)) <= 0.10
    assert abs(at(stressed, OFFSET + 120 * 60) - at(control, OFFSET + 120 * 60)) <= 0.05


def test_feedback_limits_sustained_stress():
    rec = run_stress([Event(ONSET, ONSET + 2 * HOUR, "world.threat", 0.9)], 3 * HOUR)
    cortisol = rec.column(CORTISOL)
    assert max(cortisol) < 0.7  # negative feedback keeps the axis from saturating
    assert cortisol[-1] < max(cortisol) - 0.02  # adaptation under sustained drive


@pytest.fixture(scope="module")
def a_day_and_a_half() -> Recorder:
    engine: Engine = build_minimal_human([FOOD, WATER], seed=0)
    recorder = Recorder(KEYS, every=60.0)
    engine.observe(recorder)
    engine.run(36 * HOUR)
    return recorder


def test_cortisol_awakening_response(a_day_and_a_half):
    rec = a_day_and_a_half
    sleeping, cortisol = rec.column("motor.sleeping"), rec.column(CORTISOL)
    wakes = [i for i in range(1, len(sleeping)) if sleeping[i - 1] >= 0.5 and sleeping[i] < 0.5]
    assert wakes, "the organism never woke up"
    i = wakes[0]
    pre = mean(cortisol[max(0, i - 10) : i])  # the last ~10 min of sleep
    window = cortisol[i : min(len(cortisol), i + 60)]  # the hour after waking
    peak = max(window)
    assert peak >= 1.3 * pre  # Clow et al.: +50–75%; ≥ +30% with margin
    assert 15 <= window.index(peak) <= 50  # peaks 30–45 min after waking


def test_circadian_range_stays_physiological(a_day_and_a_half):
    cortisol = a_day_and_a_half.column(CORTISOL)
    assert min(cortisol) < 0.15  # an evening trough exists
    assert max(cortisol) > 0.35  # and the morning peak reaches well above it
    assert min(cortisol) > 0.05  # never collapses to zero
