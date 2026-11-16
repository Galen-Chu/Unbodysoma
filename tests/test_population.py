"""Population layer: deterministic sampling and batch runs (Phase 2).

The acceptance of docs/VARIABILITY.md: individuals differ (no "average
man"), draws never leave the declared parameter ranges, and the same
(base_seed, index) always rebuilds the same individual.
"""

from statistics import pstdev

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.population import _spec_ranges, population_action_metrics, run_population, sample_individual
from unbodysoma.world import Event

THREAT = [Event(60.0, 90.0, "world.threat", 0.9)]


def test_draws_stay_within_declared_ranges():
    ranges = _spec_ranges()
    for index in range(30):
        for module, params in sample_individual(0, index).items():
            for name, value in params.items():
                lo, hi = ranges[(module, name)]
                assert lo <= value <= hi, f"{module}.{name}={value} outside [{lo}, {hi}]"


def test_same_seed_rebuilds_the_same_individual():
    assert sample_individual(42, 7) == sample_individual(42, 7)
    assert sample_individual(42, 7) != sample_individual(42, 8)


def test_individuals_actually_differ():
    ages = [sample_individual(0, i)["soma.cardio"]["age_years"] for i in range(40)]
    assert pstdev(ages) > 5.0  # a real spread, not the average man


def test_population_runs_are_deterministic():
    a = run_population(3, base_seed=5, seconds=120.0, builder=build_minimal_human, events=THREAT)
    b = run_population(3, base_seed=5, seconds=120.0, builder=build_minimal_human, events=THREAT)
    assert a == b


def test_population_shows_individual_differences():
    results = run_population(10, base_seed=0, seconds=150.0, builder=build_minimal_human, events=THREAT)
    peak_hr = [r.stats["soma.cardio.heart_rate"][2] for r in results]
    assert pstdev(peak_hr) > 3.0  # age, resting rate and reactivity differ between individuals
    assert all(r.rmssd_ms > 0.0 for r in results)


def test_action_shares_form_distributions():
    results = run_population(6, base_seed=1, seconds=150.0, builder=build_minimal_human, events=THREAT)
    for r in results:
        assert sum(r.action_shares.values()) == pytest.approx(1.0, abs=1e-6)
    metrics = population_action_metrics(results)
    assert sum(metrics["pooled"].values()) == pytest.approx(1.0, abs=1e-6)
    assert metrics["mean_entropy_ratio"] > 0.5  # individuals stay diverse, no mode collapse
    assert metrics["mode_amplification_ratio"] < 2.0
