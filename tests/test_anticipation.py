"""Anticipation: circadian expectations of needs, learned over days (Phase 5).

Allostasis in minimal form (Sterling, 2012): hourly profiles of hunger and
pain are learned from exposure, and the coming hour's prediction drives
action before the need arrives — heading for shelter before the predator's
usual hour, feeling hunger before the usual meal time. Acceptance below;
equations: docs/PSYCHE.md §4.11.
"""

from statistics import mean

import pytest

from unbodysoma import build_grid_human, build_minimal_human
from unbodysoma.core import BusPort, Engine, SignalBus
from unbodysoma.observe import Recorder
from unbodysoma.psyche import Anticipation
from unbodysoma.world import Event, FoodPatch, Hazard, Shelter, WaterSource

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


@pytest.mark.slow
def test_it_shelters_before_the_usual_danger_hour():
    """The grid completion scenario of Phase 5: the only food is at a patch a
    predator visits every day at the same clock hour, and a hungry organism
    must graze there. A/B on anticipation (same world, same seed): by the
    third day the intact organism is home before the hour arrives — without
    any cue at the time — and its amnesic-for-the-clock twin is not."""
    predator = Hazard(15.0, 16.0, radius=3.5, strength=0.9, start=3 * 3600.0, end=3 * 3600.0 + 2400.0, every=86400.0)

    def run_world(lesioned: bool) -> Recorder:
        engine: Engine = build_grid_human(
            food=(FoodPatch(15.0, 16.0, regrow_per_hour=1.0),),
            hazards=(predator,),
            water=(WaterSource(10.0, 4.0), WaterSource(10.0, 16.0)),
            shelters=(Shelter(10.0, 10.0),),
            start=(10.0, 10.0),
            seed=0,
            overrides={"soma.metabolism": {"initial_reserve": 0.3}},  # hungry: it grazes at the patch
        )
        if lesioned:
            engine.lesion("psyche.anticipation")
        rec = Recorder(("world.in_shelter", "intero.pain", THREAT), every=30.0)
        engine.observe(rec)
        engine.run(3 * 86400.0)
        return rec

    intact, clock_blind = run_world(False), run_world(True)

    def shelter_before_hour(rec: Recorder, day: int) -> float:
        lo, hi = day * 86400.0 + 2.0 * 3600.0, day * 86400.0 + 3.0 * 3600.0  # 10:00-11:00, predator at 11
        return mean(h for t, h in zip(rec.times(), rec.column("world.in_shelter"), strict=True) if lo <= t < hi)

    pain_day1 = max(p for t, p in zip(intact.times(), intact.column("intero.pain"), strict=True) if t < 86400.0)
    assert pain_day1 > 0.3  # the collision happened on day one...
    assert max(intact.column(THREAT)) > 0.15  # ...the danger hour was learned...
    assert shelter_before_hour(intact, 2) > shelter_before_hour(clock_blind, 2) + 0.2  # ...and it pre-shelters
