"""Instrumental learning: the law of effect through eligibility traces (Phase 4).

Anchors: Thorndike's law of effect — responses followed by satisfaction
strengthen, followed by annoyance weaken. Here: an action's value shifts by
eligibility x outcome (relief minus pain), values decay without
reinforcement, and action selection adds them to utilities. Acceptance:
tests below; equations: docs/PSYCHE.md §4.8.
"""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import BusPort, Engine, SignalBus
from unbodysoma.observe import Recorder
from unbodysoma.psyche import Instrumental
from unbodysoma.world import Event

VALUE_FLEE = "psyche.instrumental.value_flee"
VALUE_EAT = "psyche.instrumental.value_eat"
FLEE_P = "psyche.action.p_flee"
KEYS = (VALUE_FLEE, VALUE_EAT, FLEE_P)

NO_INJURY = {"soma.nociception": {"injury_gain": 0.0001}}


class _Bench:
    """Drives the module directly with scripted selection, relief and pain."""

    def __init__(self) -> None:
        self.bus = SignalBus()
        self.mod = Instrumental()
        self.module_port = BusPort(self.bus, self.mod.name, self.mod.writes)
        self.stim = BusPort(
            self.bus,
            "bench",
            ("psyche.action.selected_flee", "neuro.relief", "intero.pain"),
        )
        self.bus.commit()

    def run(self, script: "dict[str, float]", seconds: float, dt: float = 0.1) -> None:
        for i in range(round(seconds / dt)):
            self.stim.write("psyche.action.selected_flee", script.get("flee", 0.0))
            self.stim.write("neuro.relief", script.get("relief", 0.0))
            self.stim.write("intero.pain", script.get("pain", 0.0))
            self.bus.commit()
            self.module_port.time = (i + 1) * dt
            self.mod.step(dt, self.module_port)
            self.bus.commit()


def test_eligibility_bridges_action_to_delayed_outcome():
    bench = _Bench()
    bench.run({"flee": 1.0}, 10.0)  # the action happens...
    bench.run({"pain": 0.8}, 15.0)  # ...the outcome arrives within the trace
    assert bench.mod.value["flee"] < -0.02  # punished (rising-edge gated)
    bench2 = _Bench()
    bench2.run({"flee": 1.0}, 10.0)
    bench2.run({}, 600.0)  # the trace died long ago
    bench2.run({"pain": 0.8}, 10.0)
    assert bench2.mod.value["flee"] == pytest.approx(0.0, abs=1e-6)  # no credit without eligibility


def test_relief_rewards_and_values_decay():
    bench = _Bench()
    bench.run({"flee": 1.0, "relief": 0.5}, 60.0)
    assert bench.mod.value["flee"] > 0.2  # rewarded
    peak = bench.mod.value["flee"]
    bench.run({}, 3600.0)
    assert bench.mod.value["flee"] < 0.8 * peak  # forgotten without reinforcement


def run_events(events: list[Event], seconds: float, overrides: dict | None = None) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=0, overrides={**NO_INJURY, **(overrides or {})})
    recorder = Recorder(KEYS, every=2.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, lo: float, hi: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi]


def test_punished_fleeing_shy_away_from_later_threats():
    """Threats whose escape hurt: after several of them, a mild cue that used
    to barely raise fleeing raises it far less than in an unpunished control."""
    trials = []
    for i in range(6):
        t = 300.0 + 120.0 * i
        trials.extend([Event(t, t + 30.0, "world.threat", 0.9), Event(t + 5.0, t + 30.0, "world.damage", 0.8)])
    probe = Event(1200.0, 1230.0, "world.threat", 0.2)  # below the flee threshold, even attention-amplified
    punished = run_events([*trials, probe], 1250.0)
    control_events = [Event(300.0 + 120.0 * i, 300.0 + 120.0 * i + 30.0, "world.threat", 0.9) for i in range(6)]
    control = run_events([*control_events, probe], 1250.0)
    assert min(window(punished, VALUE_FLEE, 1000.0, 1200.0)) < -0.1  # the punishment landed
    assert mean(window(control, VALUE_FLEE, 1000.0, 1200.0)) == pytest.approx(0.0, abs=0.05)
    punished_p = mean(window(punished, FLEE_P, 1200.0, 1230.0))
    control_p = mean(window(control, FLEE_P, 1200.0, 1230.0))
    assert punished_p < 0.5 * control_p  # and it shows in choice


def test_meals_reward_eating():
    events = [Event(300.0, 1e9, "world.food_available", 1.0)]
    rec = run_events(events, 4000.0, {"soma.metabolism": {"initial_reserve": 0.3}})
    assert max(window(rec, VALUE_EAT, 2000.0, 4000.0)) > 0.12  # eating while it relieved earned value
