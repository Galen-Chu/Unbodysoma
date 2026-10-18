"""Acceptance tests for observation layer 5: clamp / lesion / cancel interventions."""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import HealthMonitor, Recorder, RunWriter, load_run
from unbodysoma.world import Event

THREAT = [Event(60.0, 90.0, "world.threat", 0.9)]
KEYS = (
    "soma.cardio.heart_rate",
    "intero.cardiac_arousal",
    "psyche.affect.arousal",
    "psyche.affect.valence",
    "psyche.appraisal.threat",
)


def record(engine: Engine, seconds: float = 300.0) -> Recorder:
    recorder = Recorder(KEYS, every=0.5)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, start: float, end: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if start <= t < end]


# -- clamp ------------------------------------------------------------------


def test_clamp_overrides_readers_only_inside_its_window():
    engine = build_minimal_human(seed=0)
    engine.clamp("soma.cardio.heart_rate", 100.0, start=10.0, end=20.0)
    rec = record(engine, 30.0)
    assert window(rec, "soma.cardio.heart_rate", 10.0, 20.0) == pytest.approx([100.0] * 20)
    assert max(window(rec, "soma.cardio.heart_rate", 20.0, 30.0)) < 70.0
    # Readers downstream did see the clamped value.
    assert min(window(rec, "intero.cardiac_arousal", 11.0, 20.0)) > 0.3


def test_clamp_leaves_the_writers_internal_state_alone():
    engine = build_minimal_human(seed=0)
    engine.clamp("soma.cardio.heart_rate", 150.0, start=0.0, end=20.0)
    engine.run(10.0)
    cardio = next(m for m in engine.modules if m.name == "soma.cardio")
    assert engine.bus.read("soma.cardio.heart_rate") == 150.0
    assert cardio.heart_rate < 70.0


def test_clamp_active_at_time_zero_applies_to_initial_state():
    engine = build_minimal_human()
    engine.clamp("psyche.affect.arousal", 0.9)
    engine.snapshot()  # forces setup without stepping
    assert engine.bus.read("psyche.affect.arousal") == 0.9


def test_beta_blocker_dissociates_felt_arousal_from_appraised_threat():
    """Holding HR at rest blunts arousal, yet the threat is still appraised as negative."""
    intact = record(build_minimal_human(THREAT, seed=0))
    blocked_engine = build_minimal_human(THREAT, seed=0)
    blocked_engine.clamp("soma.cardio.heart_rate", 65.0)
    blocked = record(blocked_engine)

    assert max(window(intact, "psyche.affect.arousal", 60, 100)) > 0.9
    assert max(window(blocked, "psyche.affect.arousal", 60, 100)) < 0.5
    assert mean(window(blocked, "psyche.affect.valence", 70, 90)) < -0.5


# -- lesion -----------------------------------------------------------------


def test_silenced_interoception_blunts_emotional_arousal():
    engine = build_minimal_human(THREAT, seed=0)
    engine.lesion("interface.interoception")
    rec = record(engine)
    assert max(rec.column("intero.cardiac_arousal")) == 0.0
    assert max(window(rec, "psyche.affect.arousal", 60, 100)) < 0.5
    # The body still reacts — only the mind's view of it is gone.
    assert max(window(rec, "soma.cardio.heart_rate", 60, 100)) > 140.0


def test_frozen_module_holds_outputs_and_state():
    engine = build_minimal_human(THREAT, seed=0)
    engine.run(70.0)
    held = engine.bus.read("psyche.appraisal.threat")
    appraisal = next(m for m in engine.modules if m.name == "psyche.appraisal")
    engine.lesion("psyche.appraisal", start=70.0, end=120.0, mode="freeze")
    engine.run(40.0)  # the threat ends at t = 90, but appraisal cannot notice
    assert engine.bus.read("psyche.appraisal.threat") == held
    assert appraisal.threat == held
    engine.run(20.0)
    assert engine.bus.read("psyche.appraisal.threat") < held


def test_silenced_heart_trips_the_health_monitor():
    engine = build_minimal_human(seed=0)
    engine.lesion("soma.cardio", start=30.0)
    HealthMonitor(halt_on="critical").attach(engine)
    reason = engine.run(300.0)
    assert reason is not None and "heart_rate" in reason
    assert engine.time == pytest.approx(30.0, abs=0.2)


# -- bookkeeping ------------------------------------------------------------


def test_interventions_are_logged_with_their_timing(tmp_path):
    engine = build_minimal_human(seed=0)
    with RunWriter(tmp_path / "run").attach(engine):
        engine.clamp("motor.exertion", 0.5, start=5.0, end=10.0)
        engine.lesion("psyche.drives", start=8.0)
        engine.run(20.0)

    run = load_run(tmp_path / "run")
    kinds = [(e["kind"], e["type"], e["t"]) for e in run.events]
    assert kinds == [
        ("intervention.scheduled", "clamp", 0.0),
        ("intervention.scheduled", "lesion", 0.0),
        ("intervention.started", "clamp", pytest.approx(5.0)),
        ("intervention.started", "lesion", pytest.approx(8.0)),
        ("intervention.ended", "clamp", pytest.approx(10.0)),
    ]
    assert run.events[1]["end"] is None  # open-ended: infinity is stored as null


def test_invalid_interventions_are_rejected():
    engine = build_minimal_human()
    with pytest.raises(ValueError, match="unknown signal"):
        engine.clamp("soma.cardio.nonexistent", 1.0)
    with pytest.raises(ValueError, match="unknown module"):
        engine.lesion("soma.liver")
    with pytest.raises(ValueError, match="mode"):
        engine.lesion("soma.cardio", mode="remove")
    with pytest.raises(ValueError, match="end after"):
        engine.clamp("motor.exertion", 1.0, start=5.0, end=5.0)


def test_branching_experiment_with_snapshot_and_cancel():
    """Rewind to before an intervention, cancel it, and recover the intact run exactly."""
    intact = build_minimal_human(THREAT, seed=2)
    intact.run(120.0)

    engine = build_minimal_human(THREAT, seed=2)
    engine.run(50.0)
    snap = engine.snapshot()
    lesion = engine.lesion("interface.interoception", start=50.0)
    engine.run(70.0)
    lesioned_state = engine.bus.snapshot()

    engine.restore(snap)
    engine.cancel(lesion)
    engine.run(70.0)

    assert engine.bus.snapshot() == intact.bus.snapshot()
    assert lesioned_state != intact.bus.snapshot()
    assert engine.events[-1]["kind"] == "intervention.cancelled"
