"""Acceptance tests for probabilistic action selection (ADR-0007)."""

import math
import random
from collections import Counter

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import BusPort, Engine, Module
from unbodysoma.observe import Recorder
from unbodysoma.observe.metrics import distribution, entropy_bits
from unbodysoma.psyche import ActionSelection
from unbodysoma.psyche.action import ACTIONS
from unbodysoma.psyche.policy import sample, softmax, switch
from unbodysoma.world import Event


class Constant(Module):
    """Holds a fixed internal situation, so the policy alone is under test."""

    name = "test.constant"

    def __init__(self, values: dict[str, float]) -> None:
        self.values = values
        self.writes = tuple(values)

    def setup(self, port: BusPort) -> None:
        self.step(0.0, port)

    def step(self, dt: float, port: BusPort) -> None:
        for key, value in self.values.items():
            port.write(key, value)


def choices(situation: dict[str, float], decisions: int = 2000, **params) -> Counter:
    engine = Engine()
    engine.add(Constant(situation))
    engine.add(ActionSelection(**params))
    recorder = Recorder([f"psyche.action.selected_{a}" for a in ACTIONS], every=0.5)
    engine.observe(recorder)
    engine.run(decisions / ActionSelection.rate_hz)
    counts: Counter = Counter()
    for row in recorder.rows[1:]:
        counts[ACTIONS[row[1:].index(1.0)]] += 1
    return counts


# Hunger exactly at the eating threshold with food in reach: eating and idling tie.
AMBIVALENT = {
    "psyche.appraisal.threat": 0.0,
    "psyche.drive.hunger": 0.35,
    "psyche.drive.thirst": 0.0,
    "psyche.drive.thermal_discomfort": 0.0,
    "psyche.drive.sleepiness": 0.0,
    "extero.food": 1.0,
    "extero.water": 0.0,
    "extero.in_shelter": 0.0,
    "extero.shelter_known": 0.0,
}
# No commitment bonuses, and fast reconsideration so that 2000 decisions sample the long-run budget well.
NO_BIAS = {"stickiness": 0.0, "eat_commitment": 0.0, "reconsideration_rate": 1.0}


# -- the policy functions ----------------------------------------------------


def test_softmax_is_a_probability_distribution():
    p = softmax({"a": 1.0, "b": 0.5, "c": -2.0}, 0.3)
    assert sum(p.values()) == pytest.approx(1.0)
    assert p["a"] > p["b"] > p["c"] > 0.0


def test_softmax_ignores_a_common_offset_and_ties_are_uniform():
    assert softmax({"a": 1.0, "b": 2.0}, 0.5) == pytest.approx(softmax({"a": 101.0, "b": 102.0}, 0.5))
    assert softmax({"a": 0.0, "b": 0.0}, 0.1) == pytest.approx({"a": 0.5, "b": 0.5})


def test_zero_temperature_is_argmax():
    assert softmax({"a": 0.1, "b": 0.2, "c": 0.2}, 0.0) == {"a": 0.0, "b": 1.0, "c": 0.0}


def test_sampling_matches_the_probabilities():
    rng = random.Random(0)
    p = {"a": 0.6, "b": 0.3, "c": 0.1}
    counts = Counter(sample(p, rng) for _ in range(100_000))
    for k, v in p.items():
        assert counts[k] / 100_000 == pytest.approx(v, abs=0.01)


def test_switching_does_not_depend_on_how_often_decisions_are_taken():
    """The flaw that fragmented sleep and meals: per-decision sampling made long behaviours leak."""
    utilities = {"sleep": 0.3, "eat": 0.1, "idle": 0.0}  # sleep is clearly preferred

    def switches_per_hour(dt: float) -> float:
        rng, current, changes = random.Random(0), "sleep", 0
        for _ in range(round(200 * 3600 / dt)):  # 200 simulated hours
            new = switch(current, utilities, 0.015, 1 / 60, dt, rng)
            changes += new != current
            current = "sleep"  # always restart from sleep: measures the hazard of leaving it
        return changes / 200

    fine, coarse = switches_per_hour(0.5), switches_per_hour(5.0)
    assert fine < 0.2  # leaving a clearly preferred action is rare...
    assert fine == pytest.approx(coarse, abs=0.05)  # ...and equally rare at any decision rate


def test_an_urgent_alternative_wins_at_once():
    rng = random.Random(0)
    assert switch("sleep", {"sleep": 0.5, "flee": 1.5}, 0.015, 1 / 60, 0.5, rng) == "flee"


def test_zero_temperature_switches_only_to_something_strictly_better():
    rng = random.Random(0)
    assert switch("idle", {"idle": 0.0, "eat": 0.0}, 0.0, 1.0, 0.5, rng) == "idle"
    assert switch("idle", {"idle": 0.0, "eat": 0.1}, 0.0, 1.0, 0.5, rng) == "eat"


def test_an_unavailable_action_forces_a_fresh_choice():
    rng = random.Random(0)
    assert switch("eat", {"idle": 0.0, "explore": -5.0}, 0.015, 1 / 60, 0.5, rng) == "idle"


def test_long_run_time_budget_follows_the_softmax():
    """Detailed balance: the time budget is softmax(u, T). Holds when rate * dt is small (one jump per step)."""
    rng, current = random.Random(1), "a"
    utilities = {"a": 0.0, "b": 0.05, "c": -0.05}
    counts: Counter = Counter()
    for _ in range(400_000):
        current = switch(current, utilities, 0.05, 0.1, 0.5, rng)
        counts[current] += 1
    for k, p in softmax(utilities, 0.05).items():
        assert counts[k] / 400_000 == pytest.approx(p, abs=0.02)


# -- behaviour ----------------------------------------------------------------


def test_an_ambivalent_choice_splits_evenly():
    counts = choices(AMBIVALENT, **NO_BIAS)
    assert set(counts) == {"idle", "eat"}
    assert counts["eat"] / sum(counts.values()) == pytest.approx(0.5, abs=0.05)


def test_zero_temperature_collapses_to_a_single_choice():
    """The LLM "always 7" failure, reproduced on purpose: no variability at all."""
    assert entropy_bits(distribution(choices(AMBIVALENT, temperature=0.0, **NO_BIAS))) == 0.0


def test_choice_entropy_grows_with_temperature():
    situation = {**AMBIVALENT, "psyche.drive.hunger": 0.42}
    entropies = [
        entropy_bits(distribution(choices(situation, temperature=t, **NO_BIAS))) for t in (0.0, 0.03, 0.1, 1.0)
    ]
    assert entropies == sorted(entropies)
    assert entropies[0] == 0.0 and entropies[-1] > 0.9


def test_published_probabilities_always_sum_to_one():
    engine = build_minimal_human([Event(10.0, 20.0, "world.threat", 0.9)])
    recorder = Recorder([f"psyche.action.p_{a}" for a in ACTIONS], every=0.5)
    engine.observe(recorder)
    engine.run(40.0)
    for row in recorder.rows:
        assert math.fsum(row[1:]) == pytest.approx(1.0)


def test_individuals_end_their_meals_differently():
    """Same situation, different seeds: variability between individuals, reproducibility within."""

    def meal_end(seed: int) -> float:
        engine = build_minimal_human(
            [Event(0.0, 1e9, "world.food_available", 1.0)],
            seed=seed,
            overrides={"soma.metabolism": {"initial_reserve": 0.4}},
        )
        recorder = Recorder(["motor.eating", "psyche.drive.hunger"], every=1.0)
        engine.observe(recorder)
        engine.run(1800.0)
        eating = recorder.column("motor.eating")
        return recorder.column("psyche.drive.hunger")[max(i for i, e in enumerate(eating) if e == 1.0)]

    ends = [meal_end(seed) for seed in range(4)]
    assert len(set(ends)) == 4
    assert all(0.05 < e < 0.2 for e in ends)
    assert meal_end(1) == ends[1]
