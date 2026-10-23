"""Acceptance tests for structured noise, heart-rate variability and distribution metrics (docs/VARIABILITY.md)."""

import math
import random
from statistics import mean, pstdev

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import ou_step
from unbodysoma.observe import Recorder
from unbodysoma.observe.metrics import (
    entropy_bits,
    entropy_ratio,
    mode_amplification_ratio,
    rmssd_ms,
    rr_intervals,
    sdnn_ms,
)
from unbodysoma.world import Event

# -- Ornstein-Uhlenbeck noise -------------------------------------------------


def ou_series(dt: float, n: int, tau: float = 10.0, sigma: float = 2.0, seed: int = 0) -> list[float]:
    rng, x, xs = random.Random(seed), 0.0, []
    for _ in range(n):
        x = ou_step(x, dt, tau, sigma, rng)
        xs.append(x)
    return xs


def autocorrelation(xs: list[float], lag: int) -> float:
    m, var = mean(xs), pstdev(xs) ** 2
    return mean((a - m) * (b - m) for a, b in zip(xs, xs[lag:], strict=False)) / var


def test_ou_has_the_requested_spread_and_memory():
    xs = ou_series(dt=0.5, n=200_000)
    assert mean(xs) == pytest.approx(0.0, abs=0.1)
    assert pstdev(xs) == pytest.approx(2.0, rel=0.05)
    assert autocorrelation(xs, lag=20) == pytest.approx(math.exp(-1.0), abs=0.05)  # lag 20 * 0.5 s = tau


def test_ou_statistics_do_not_depend_on_step_size():
    fine, coarse = ou_series(dt=0.1, n=100_000), ou_series(dt=5.0, n=100_000)
    assert pstdev(fine) == pytest.approx(pstdev(coarse), rel=0.1)


# -- heart-rate variability ---------------------------------------------------


def heart_rate_trace(events=(), seconds: float = 300.0, seed: int = 0, **cardio):
    engine = build_minimal_human(events, seed=seed, overrides={"soma.cardio": cardio} if cardio else None)
    recorder = Recorder(["soma.cardio.heart_rate"], every=0.1)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder.times(), recorder.column("soma.cardio.heart_rate")


def window_rr(times, hr, start: float, end: float) -> list[float]:
    kept = [(t, h) for t, h in zip(times, hr, strict=True) if start <= t < end]
    return rr_intervals([t for t, _ in kept], [h for _, h in kept])


def test_resting_hrv_is_in_a_physiological_range():
    rr = window_rr(*heart_rate_trace(), 0.0, 300.0)
    assert 60.0 / mean(rr) == pytest.approx(65.0, abs=2.0)  # mean heart rate
    assert 15.0 < rmssd_ms(rr) < 100.0
    assert 15.0 < sdnn_ms(rr) < 150.0


def test_stress_suppresses_hrv():
    times, hr = heart_rate_trace([Event(0.0, 600.0, "world.threat", 0.9)], seconds=200.0)
    stressed = rmssd_ms(window_rr(times, hr, 60.0, 200.0))
    times, hr = heart_rate_trace(seconds=200.0)
    relaxed = rmssd_ms(window_rr(times, hr, 60.0, 200.0))
    assert stressed < 0.5 * relaxed


def test_without_variability_the_heart_is_metronomic():
    """The "loss of complexity" control: switching HRV off leaves an unnaturally regular heartbeat."""
    rr = window_rr(*heart_rate_trace(rsa_amplitude=0.0, lf_sigma=0.0), 0.0, 300.0)
    assert rmssd_ms(rr) < 1.0


def test_individuals_differ_but_each_is_reproducible():
    a, b = heart_rate_trace(seed=1, seconds=30.0)[1], heart_rate_trace(seed=2, seconds=30.0)[1]
    assert a != b
    assert heart_rate_trace(seed=1, seconds=30.0)[1] == a


# -- metric definitions -------------------------------------------------------


def test_rr_intervals_of_a_steady_heart():
    times = [i * 0.1 for i in range(601)]
    rr = rr_intervals(times, [60.0] * len(times))
    assert rr == pytest.approx([1.0] * len(rr))
    assert len(rr) == 59
    assert rmssd_ms(rr) == pytest.approx(0.0, abs=1e-6)


def test_distribution_metrics():
    # Illustrative "pick a number from 1 to 10" answers (not real data): 7 is the human mode.
    human = {"7": 30, "3": 15, "5": 12, "4": 10, "8": 10, "2": 8, "6": 8, "9": 4, "1": 2, "10": 1}
    collapsed = {"7": 90, "3": 5, "5": 3, "4": 2}
    assert entropy_bits({"a": 1.0}) == 0.0
    assert entropy_bits({"a": 0.5, "b": 0.5}) == pytest.approx(1.0)
    assert mode_amplification_ratio(human, human) == pytest.approx(1.0)
    assert mode_amplification_ratio(collapsed, human) == pytest.approx(3.0)
    assert entropy_ratio(collapsed, human) < 0.5
    with pytest.raises(ValueError, match="sum to 1"):
        entropy_bits({"a": 3, "b": 1})  # raw counts are rejected, not silently misread
