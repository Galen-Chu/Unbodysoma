"""Acceptance tests for observation layers 1-2: run records and health monitoring."""

import math

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import BusPort, Engine, Module
from unbodysoma.observe import FiniteRule, HealthMonitor, RangeRule, Recorder, RunWriter, SustainedRule, load_run
from unbodysoma.observe.behavior import episodes, per_day, time_fraction
from unbodysoma.world import Event

THREAT = [Event(60.0, 90.0, "world.threat", 0.9)]
PROLONGED_THREAT = [Event(10.0, 200.0, "world.threat", 0.9)]


class Diverging(Module):
    """Writes NaN from t = 1 s, standing in for a numerically unstable model."""

    name = "test.diverging"
    writes = ("test.value",)

    def step(self, dt: float, port: BusPort) -> None:
        port.write("test.value", math.nan if port.time >= 1.0 else 0.0)


# -- layer 1: run records ----------------------------------------------------


def test_run_record_round_trips(tmp_path):
    engine = build_minimal_human(THREAT, seed=0)
    recorder = Recorder(["soma.cardio.heart_rate"], every=1.0)
    engine.observe(recorder)
    with RunWriter(tmp_path / "run", every=1.0, config={"scenario": "fear", "seed": 0}).attach(engine):
        engine.run(120.0)

    run = load_run(tmp_path / "run")
    assert run.meta["config"] == {"scenario": "fear", "seed": 0}
    assert run.meta["ticks"] == 12000
    assert [m["name"] for m in run.meta["modules"]] == [m.name for m in engine.modules]
    assert set(run.columns) == set(engine.signals())
    assert len(run.times) == 121
    assert run.column("soma.cardio.heart_rate") == pytest.approx(recorder.column("soma.cardio.heart_rate"))


def test_signals_not_yet_published_are_blank_not_zero(tmp_path):
    engine = build_minimal_human()
    with RunWriter(tmp_path / "run", every=1.0).attach(engine):
        engine.run(1.0)
    run = load_run(tmp_path / "run")
    # Exteroception publishes nothing in setup, so at t = 0 there is no value yet.
    assert run.column("extero.threat")[0] is None
    assert run.column("extero.threat")[1] is not None


def test_events_from_before_attaching_are_kept(tmp_path):
    engine = build_minimal_human()
    engine.lesion("psyche.drives", start=1.0)
    with RunWriter(tmp_path / "run").attach(engine):
        engine.run(2.0)
    kinds = [e["kind"] for e in load_run(tmp_path / "run").events]
    assert kinds == ["intervention.scheduled", "intervention.started"]


def test_engine_keeps_running_after_the_record_is_closed(tmp_path):
    engine = build_minimal_human()
    with RunWriter(tmp_path / "run", every=1.0).attach(engine):
        engine.run(5.0)
    engine.lesion("psyche.drives")  # an event after closing
    engine.run(5.0)
    run = load_run(tmp_path / "run")
    assert run.times[-1] == pytest.approx(5.0)
    assert run.meta["ticks"] == 500
    assert run.events == []


def test_observers_attached_mid_run_sample_on_their_own_clock(tmp_path):
    """Regression: a sampling clock starting at 0 made late observers record every tick to catch up."""
    engine = build_minimal_human()
    engine.run(100.0)
    recorder = Recorder(["soma.cardio.heart_rate"], every=10.0)
    engine.observe(recorder)
    monitor = HealthMonitor([FiniteRule()], every=10.0)
    monitor.attach(engine)
    evaluations: list[float] = []
    original = monitor.rules[0].violations
    monitor.rules[0].violations = lambda t, bus: evaluations.append(t) or original(t, bus)  # type: ignore[method-assign]
    with RunWriter(tmp_path / "run", every=10.0).attach(engine):
        engine.run(30.0)
    assert recorder.times() == pytest.approx([100.01, 110.01, 120.01])
    assert load_run(tmp_path / "run").times == pytest.approx([100.01, 110.01, 120.01])
    assert evaluations == pytest.approx([100.01, 110.01, 120.01])


def test_observers_do_not_change_results(tmp_path):
    bare = build_minimal_human(THREAT, seed=5)
    bare.run(150.0)

    watched = build_minimal_human(THREAT, seed=5)
    watched.observe(Recorder(watched.signals(), every=0.01))
    HealthMonitor(every=0.01).attach(watched)
    with RunWriter(tmp_path / "run", every=0.01).attach(watched):
        watched.run(150.0)

    assert watched.bus.snapshot() == bare.bus.snapshot()


# -- layer 2: health monitoring ---------------------------------------------


def test_normal_fear_response_raises_no_alerts():
    engine = build_minimal_human(THREAT, seed=0)
    monitor = HealthMonitor().attach(engine)
    engine.run(300.0)
    assert monitor.alerts == []


def test_prolonged_fear_is_flagged_and_then_cleared(tmp_path):
    engine = build_minimal_human(PROLONGED_THREAT, seed=0)
    monitor = HealthMonitor().attach(engine)
    with RunWriter(tmp_path / "run").attach(engine):
        engine.run(300.0)

    raised = [a for a in monitor.alerts if a.raised]
    cleared = [a for a in monitor.alerts if not a.raised]
    assert [a.rule for a in raised] == ["prolonged_negative_valence"]
    assert 130.0 <= raised[0].t <= 140.0  # valence turns negative ~t=12, flagged 120 s later
    assert [a.rule for a in cleared] == ["prolonged_negative_valence"]
    assert monitor.active == {}

    run = load_run(tmp_path / "run")
    assert [e["rule"] for e in run.events_of("health.alert")] == ["prolonged_negative_valence"]
    assert len(run.events_of("health.cleared")) == 1


def test_critical_alert_halts_the_run():
    engine = Engine()
    engine.add(Diverging())
    monitor = HealthMonitor([FiniteRule()], every=0.01, halt_on="critical").attach(engine)

    reason = engine.run(10.0)

    assert reason is not None and reason.startswith("health:")
    assert engine.time == pytest.approx(1.0)
    assert monitor.worst == "critical"
    assert [e["kind"] for e in engine.events] == ["health.alert", "engine.stopped"]


def test_warnings_do_not_halt_unless_asked():
    engine = Engine()
    engine.add(Diverging())
    HealthMonitor([RangeRule("test.value", 1.0, 2.0)], every=0.1, halt_on="critical").attach(engine)
    assert engine.run(2.0) is None


def test_breakpoint_pauses_and_run_can_resume():
    engine = build_minimal_human(THREAT, seed=0)
    reason = engine.run(300.0, until=lambda bus: bus.read("soma.cardio.heart_rate") > 120.0)
    assert reason == "breakpoint"
    assert 60.0 < engine.time < 70.0
    assert engine.run(10.0) is None


def test_sustained_rule_needs_exactly_one_threshold():
    with pytest.raises(ValueError):
        SustainedRule("x", 1.0)
    with pytest.raises(ValueError):
        SustainedRule("x", 1.0, below=0.0, above=1.0)


def test_behaviour_episodes_and_summaries():
    times = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 86400.0, 86401.0]
    values = [0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0]
    found = episodes(times, values)
    assert [(e.start, e.end) for e in found] == [
        (1.0, 3.0),
        (4.0, 5.0),
        (86400.0, 86401.0),
    ]  # last one closed at the end
    assert found[0].duration == 2.0
    assert per_day(found, 2) == [2, 1]
    assert time_fraction(values, 0.5) == pytest.approx(5 / 8)
    with pytest.raises(ValueError):
        episodes([0.0], [1.0, 2.0])
