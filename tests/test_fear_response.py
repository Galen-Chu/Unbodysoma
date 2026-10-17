"""Behavioural regression tests for the Phase 0 organism."""

from statistics import mean

from unbodysoma import build_minimal_human
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

KEYS = (
    "soma.cardio.heart_rate",
    "soma.endocrine.adrenaline",
    "psyche.affect.valence",
    "motor.exertion",
)


def run(seed: int = 0, threat: float = 0.9) -> Recorder:
    engine = build_minimal_human(events=[Event(60.0, 90.0, "world.threat", threat)], seed=seed)
    recorder = Recorder(KEYS, every=1.0)
    engine.observe(recorder)
    engine.run(300.0)
    return recorder


def window(rec: Recorder, key: str, start: float, end: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if start <= t < end]


def test_threat_raises_heart_rate_and_it_recovers():
    rec = run()
    baseline = mean(window(rec, "soma.cardio.heart_rate", 30, 60))
    during = mean(window(rec, "soma.cardio.heart_rate", 75, 90))
    after = mean(window(rec, "soma.cardio.heart_rate", 280, 300))
    assert during > baseline + 40
    assert after < baseline + 5


def test_threat_triggers_flight_and_negative_valence():
    rec = run()
    assert max(window(rec, "motor.exertion", 60, 90)) > 0.5
    assert max(window(rec, "motor.exertion", 200, 300)) < 0.05
    assert mean(window(rec, "psyche.affect.valence", 70, 90)) < -0.5
    assert mean(window(rec, "psyche.affect.valence", 0, 60)) > 0.0


def test_weak_threat_does_not_trigger_flight():
    rec = run(threat=0.2)
    assert max(rec.column("motor.exertion")) < 0.05


def test_same_seed_is_deterministic():
    assert run(seed=7).rows == run(seed=7).rows
