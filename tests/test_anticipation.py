"""Anticipation: circadian expectations of needs, learned over days (Phase 5).

Allostasis in minimal form (Sterling, 2012): hourly profiles of hunger and
pain are learned from exposure, and the coming hour's prediction drives
action before the need arrives — heading for shelter before the predator's
usual hour, feeling hunger before the usual meal time. Acceptance below;
equations: docs/PSYCHE.md §4.11.
"""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import BusPort, Engine, SignalBus
from unbodysoma.observe import Recorder
from unbodysoma.psyche import Anticipation
from unbodysoma.world import Event

HUNGER = "psyche.anticipation.hunger"
THREAT = "psyche.anticipation.threat"
CLOCK = "soma.circadian.clock_hour"


class _Bench:
    """Drives the module directly with a scripted clock, hunger and pain."""

    def __init__(self) -> None:
        self.bus = SignalBus()
        self.mod = Anticipation(tau_exposure=3600.0)
        self.module_port = BusPort(self.bus, self.mod.name, self.mod.writes)
        self.stim = BusPort(self.bus, "bench", ("psyche.drive.hunger", "intero.pain", CLOCK))
        self.bus.commit()

    def run(self, hour: float, hunger: float, pain: float, seconds: float, dt: float = 1.0) -> None:
        for i in range(round(seconds / dt)):
            self.stim.write("psyche.drive.hunger", hunger)
            self.stim.write("intero.pain", pain)
            self.stim.write(CLOCK, hour)
            self.bus.commit()
            self.module_port.time = (i + 1) * dt
            self.mod.step(dt, self.module_port)
            self.bus.commit()


def test_daily_pain_teaches_its_hour():
    bench = _Bench()
    for _ in range(3):  # three days of exposure
        bench.run(hour=17.0, hunger=0.0, pain=0.8, seconds=1800.0)  # pain during hour 17
        bench.run(hour=18.0, hunger=0.0, pain=0.0, seconds=3600.0)
    assert bench.mod.pain_bins[17] > 0.3  # the hour learned its danger
    assert bench.mod.pain_bins[18] == pytest.approx(0.0, abs=1e-3)


def test_prediction_reads_the_coming_hour():
    bench = _Bench()
    for _ in range(5):
        bench.run(hour=11.0, hunger=0.7, pain=0.0, seconds=1800.0)  # hungry around noon
        bench.run(hour=12.0, hunger=0.0, pain=0.0, seconds=1800.0)
    bench.run(hour=10.9, hunger=0.0, pain=0.0, seconds=10.0)  # standing at 10:54
    assert bench.bus.read(HUNGER) > 0.25  # it already expects the coming hunger


def test_meal_time_is_felt_before_the_meal():
    """Two days of food at a fixed clock hour: on the third, hunger rises
    before the food appears (cephalic-phase hunger, minimally)."""
    meal_hour = 14.0  # 14:00 on the clock; the default start_hour is 8
    events = [Event(0.0, 1e9, "world.food_available", 0.0)]
    for day in range(2):
        t = day * 86400.0
        events.append(
            Event(t + (meal_hour - 8.0) * 3600.0, t + (meal_hour - 7.0) * 3600.0, "world.food_available", 1.0)
        )
    engine: Engine = build_minimal_human(events, seed=0, overrides={"soma.metabolism": {"initial_reserve": 0.35}})
    rec = Recorder((HUNGER, "psyche.drive.hunger", CLOCK), every=60.0)
    engine.observe(rec)
    engine.run(2.6 * 86400.0)
    # The hour before the third meal time: anticipation is high and felt.
    pre_meal = [
        h
        for t, h, a in zip(rec.times(), rec.column(HUNGER), rec.column(CLOCK), strict=True)
        if 2 * 86400.0 <= t < 2.6 * 86400.0 and meal_hour - 1.4 <= a < meal_hour - 0.2
    ]
    assert mean(pre_meal) > 0.15


# -- the grid-level claim, honestly measured out -------------------------------
#
# The original slow test here asserted an A/B on a grid world (predator at
# the food patch, same clock hour daily): the intact organism home before
# the usual danger hour on day 3, its clock-blind twin not. Nine seed-family
# probes (2026-11-27) showed the contrast is not measurable in this world's
# economics:
#
# - The blind twin's mid-morning location is the product of place memory x
#   instrumental learning x food economics (sated rest at home, or
#   eat-aversion after the day-1 bite, or danger-field repulsion) - a
#   structural attractor, so the control arm saturates at "home" (1.0) on
#   any reshuffled trajectory; the A/B margin has nothing to express.
# - The within-organism contrast is vacuous for the same reason: day-3
#   pre-hour homing is the default sated-rest behavior (present with
#   anticipation lesioned, and even when the hour was never learned).
# - Day-1 exposure itself (pain > 0.3) is schedule luck (seeds gave 0.89,
#   0.51, 0.23); making food abundant removes the collision entirely, and
#   global daily storms starve the organism (the pain-avoidance cascade).
#
# Anticipation's acceptance therefore rests on the deterministic tests
# above (module-level hour learning, next-hour prediction, cephalic-phase
# hunger in a scripted world). Revisit a world-level demonstration when
# foraging pressure is strong enough to keep both arms structurally out
# at the critical hour.
