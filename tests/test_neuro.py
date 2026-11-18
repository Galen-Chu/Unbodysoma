"""Neuromodulation: reward (dopamine), mood tone (serotonin), vigilance (NE).

Anchors: dopamine as the phasic response to unexpected reward (Schultz et al.
1997) — here the minimal, prediction-free form: a burst proportional to how
much felt homeostatic error a recovering behaviour actually removes; serotonin
tone dragged down by chronic pain and deficit (Dayan & Huys 2009); norepinephrine
consolidating threat, pain and cardiac arousal into vigilance that biases
appraisal (Aston-Jones & Cohen 2005). Bounds are coarse as everywhere here:
we pin the shape of each phenomenon. See docs/SOMA.md §2.10.
"""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

DA = "neuro.dopamine"
HT = "neuro.serotonin"
NE = "neuro.norepinephrine"
VALENCE = "psyche.affect.valence"
THREAT = "psyche.appraisal.threat"
KEYS = (DA, HT, NE, VALENCE, THREAT, "motor.eating")


def run_events(events: list[Event], seconds: float, overrides: dict | None = None) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=0, overrides=overrides)
    recorder = Recorder(KEYS, every=2.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, lo: float, hi: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi]


@pytest.fixture(scope="module")
def hungry_meal() -> Recorder:
    return run_events(
        [Event(300.0, 1e9, "world.food_available", 1.0)], 3600.0, {"soma.metabolism": {"initial_reserve": 0.3}}
    )


@pytest.fixture(scope="module")
def sated_meal() -> Recorder:
    return run_events(
        [Event(300.0, 1e9, "world.food_available", 1.0)], 1800.0, {"soma.metabolism": {"initial_reserve": 0.78}}
    )


# -- dopamine: reward as relief ---------------------------------------------


def test_hungry_meal_bursts_dopamine(hungry_meal: Recorder):
    rec = hungry_meal
    assert mean(window(rec, "motor.eating", 300.0, 2000.0)) > 0.2  # it actually ate
    assert max(window(rec, DA, 0.0, 300.0)) < 0.6  # tonic before the meal
    assert max(window(rec, DA, 300.0, 2500.0)) > 0.75  # recovering is a burst
    assert mean(window(rec, DA, 2500.0, 3000.0)) < 0.62  # and it returns toward tonic


def test_food_when_sated_barely_rewards(sated_meal: Recorder):
    rec = sated_meal
    assert mean(window(rec, "motor.eating", 300.0, 900.0)) < 0.1  # it is not interested
    assert max(window(rec, DA, 300.0, 1800.0)) < 0.62  # no relief to reward


def test_relief_feels_good(hungry_meal: Recorder):
    rec = hungry_meal
    mid_meal = mean(window(rec, VALENCE, 500.0, 900.0))
    after = mean(window(rec, VALENCE, 1500.0, 1800.0))
    before = mean(window(rec, VALENCE, 100.0, 300.0))
    assert mid_meal > after or mid_meal > before  # eating lifts mood above its surroundings


# -- serotonin: chronic bad states read as low mood --------------------------


def test_sustained_pain_lowers_serotonin_and_mood():
    """Isolated to the serotonin axis: injury gain ~0, so felt pain tracks the
    stimulus instead of outlasting it for hours (which is nociception's own,
    separately tested behaviour)."""
    rec = run_events(
        [Event(300.0, 1200.0, "world.damage", 0.5)],
        4200.0,
        {"soma.nociception": {"injury_gain": 0.0001}},
    )
    rest = mean(window(rec, HT, 100.0, 300.0))
    low = min(window(rec, HT, 1000.0, 1200.0))
    assert low < rest - 0.15  # tone falls under sustained pain
    assert mean(window(rec, VALENCE, 1000.0, 1200.0)) < mean(window(rec, VALENCE, 100.0, 300.0)) - 0.05
    late = mean(window(rec, HT, 4000.0, 4200.0))
    assert late > low + 0.05  # and recovers once the pain clears


# -- norepinephrine: vigilance biases appraisal --------------------------------


def test_pain_makes_mild_threats_look_worse():
    calm = run_events([Event(600.0, 800.0, "world.threat", 0.2)], 1000.0)
    hurt = run_events([Event(300.0, 700.0, "world.damage", 0.8), Event(600.0, 800.0, "world.threat", 0.2)], 1000.0)
    assert mean(window(hurt, NE, 550.0, 600.0)) > 0.4  # pain alone raises vigilance
    calm_threat = mean(window(calm, THREAT, 620.0, 780.0))
    hurt_threat = mean(window(hurt, THREAT, 620.0, 780.0))
    assert hurt_threat > calm_threat + 0.02  # the same mild cue reads as more threatening


def test_vigilance_decays_after_the_stimulus():
    rec = run_events([Event(300.0, 400.0, "world.threat", 0.9)], 600.0)
    assert max(window(rec, NE, 350.0, 420.0)) > 0.5
    assert window(rec, NE, 580.0, 600.0)[-1] < 0.15  # back down within minutes
