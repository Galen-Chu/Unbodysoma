"""Literature-curve validation of the respiratory module (Phase 2).

Anchors: normal adult resting rate 12–20 breaths/min (Cretikos et al., 2008);
target SpO₂ 94–98 % for most adults (O'Driscoll et al., 2008). See
docs/SOMA.md §2.8.
"""

from statistics import mean

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder

RATE = "soma.respiration.rate"
VE = "soma.respiration.minute_ventilation"
SPO2 = "soma.respiration.spo2"
KEYS = (RATE, VE, SPO2)


def run(
    seconds: float, overrides: dict | None = None, clamp_exertion: tuple[float, float, float] | None = None
) -> Recorder:
    engine: Engine = build_minimal_human([], seed=0, overrides=overrides)
    if clamp_exertion:
        engine.clamp("motor.exertion", *clamp_exertion)
    recorder = Recorder(KEYS, every=5.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, start: float, end: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if start <= t < end]


def test_resting_rate_is_in_the_normal_band():
    rec = run(300.0)
    resting = mean(window(rec, RATE, 200, 300))
    assert 12.0 <= resting <= 20.0  # Cretikos et al. (2008)


def test_resting_saturation_is_in_the_target_range():
    rec = run(300.0)
    resting = mean(window(rec, SPO2, 200, 300))
    assert 94.0 <= resting <= 98.0  # O'Driscoll et al. (2008)


def test_exercise_raises_rate_and_ventilation_but_keeps_saturation_healthy():
    rec = run(600.0, clamp_exertion=(0.7, 200.0, 600.0))
    rate = mean(window(rec, RATE, 500, 600))
    ventilation = mean(window(rec, VE, 500, 600))
    spo2 = min(window(rec, SPO2, 200, 600))
    assert 20.0 < rate <= 35.0  # moderate exercise lifts the rate out of the resting band
    assert ventilation > 3.0 * 6.0  # ventilation triples or more from rest
    assert spo2 >= 94.0  # healthy exercise desaturation stays small


def test_signals_stay_within_declared_ranges():
    rec = run(600.0, clamp_exertion=(1.0, 0.0, 600.0))
    assert 4.0 <= min(rec.column(RATE)) and max(rec.column(RATE)) <= 60.0
    assert 2.0 <= min(rec.column(VE)) and max(rec.column(VE)) <= 120.0
    assert min(rec.column(SPO2)) >= 94.0  # even at full exertion, a healthy organism


def test_run_is_deterministic_for_a_seed():
    assert run(120.0).rows == run(120.0).rows
