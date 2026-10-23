"""Acceptance tests for the circadian clock and sleep (two-process model). Multi-hour simulations."""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

pytestmark = pytest.mark.slow

HOUR = 3600.0
FOOD = Event(0.0, 1e9, "world.food_available", 1.0)
WATER = Event(0.0, 1e9, "world.water_available", 1.0)
KEYS = (
    "motor.sleeping",
    "motor.exertion",
    "soma.circadian.clock_hour",
    "soma.cardio.heart_rate",
    "soma.endocrine.cortisol",
    "soma.sleep.pressure",
    "psyche.drive.hunger",
)


def simulate(hours: float, events=(FOOD, WATER), seed: int = 0, setup=None, every: float = 60.0) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=seed, base_dt=0.05)  # starts at 08:00
    if setup:
        setup(engine)
    recorder = Recorder(KEYS, every=every)
    engine.observe(recorder)
    engine.run(hours * HOUR)
    return recorder


def sleep_episodes(rec: Recorder) -> list[tuple[float, float]]:
    episodes, start = [], None
    for t, asleep in zip(rec.times(), rec.column("motor.sleeping"), strict=True):
        if asleep and start is None:
            start = t
        elif not asleep and start is not None:
            episodes.append((start, t))
            start = None
    return episodes


def clock_at(t: float) -> float:
    return (8.0 + t / HOUR) % 24.0


@pytest.fixture(scope="module")
def two_days() -> Recorder:
    return simulate(48.0)


def test_one_consolidated_sleep_per_night(two_days):
    episodes = sleep_episodes(two_days)
    assert len(episodes) == 2
    for start, end in episodes:
        assert 21.0 <= clock_at(start) <= 24.0  # bedtime in the late evening
        assert 5.0 <= clock_at(end) <= 8.0  # wakes in the early morning
        assert 6.5 * HOUR <= end - start <= 9.0 * HOUR


def test_sleep_slows_the_heart_and_cortisol_peaks_in_the_morning(two_days):
    asleep = [
        h
        for h, s in zip(two_days.column("soma.cardio.heart_rate"), two_days.column("motor.sleeping"), strict=True)
        if s
    ]
    awake = [
        h
        for h, s in zip(two_days.column("soma.cardio.heart_rate"), two_days.column("motor.sleeping"), strict=True)
        if not s
    ]
    assert mean(awake) - mean(asleep) > 5.0
    cortisol = list(
        zip(two_days.column("soma.circadian.clock_hour"), two_days.column("soma.endocrine.cortisol"), strict=True)
    )
    morning = mean(c for h, c in cortisol if 7.0 <= h < 10.0)
    evening = mean(c for h, c in cortisol if 19.0 <= h < 22.0)
    assert morning > evening + 0.1


def test_hunger_is_muted_in_sleep_and_returns_on_waking(two_days):
    _, end = sleep_episodes(two_days)[0]
    times, hunger = two_days.times(), two_days.column("psyche.drive.hunger")
    last_hour_asleep = mean(h for t, h in zip(times, hunger, strict=True) if end - HOUR <= t < end)
    just_awake = max(h for t, h in zip(times, hunger, strict=True) if end <= t < end + 10 * 60)
    assert just_awake > last_hour_asleep + 0.05


def test_sleep_pressure_follows_the_two_process_shape(two_days):
    pressure = two_days.column("soma.sleep.pressure")
    (start, end), _ = sleep_episodes(two_days)
    at = {round(t): p for t, p in zip(two_days.times(), pressure, strict=True)}
    assert at[round(start)] > 0.5 and at[round(end)] < 0.2  # built up by day, discharged by night


def test_a_threat_wakes_the_sleeper_who_then_sleeps_again():
    at_2am = 18.0 * HOUR
    rec = simulate(22.0, events=(FOOD, WATER, Event(at_2am, at_2am + 60.0, "world.threat", 0.9)), every=10.0)
    times, sleeping, exertion = rec.times(), rec.column("motor.sleeping"), rec.column("motor.exertion")
    assert all(s for t, s in zip(times, sleeping, strict=True) if at_2am - 600 <= t < at_2am)  # soundly asleep before
    assert max(e for t, e in zip(times, exertion, strict=True) if at_2am <= t < at_2am + 90) > 0.5  # woke and fled
    assert any(
        s for t, s in zip(times, sleeping, strict=True) if at_2am + 600 <= t < at_2am + 2 * HOUR
    )  # back to sleep


def test_sleep_deprivation_builds_pressure_that_forces_sleep_at_an_odd_hour():
    released = 30.0 * HOUR  # 14:00 on day 2, after a night without sleep

    def deprive(engine: Engine) -> None:
        engine.clamp("motor.sleeping", 0.0, end=released)

    deprived = simulate(31.0, setup=deprive)
    control = simulate(31.0)
    pressure_at_release = deprived.column("soma.sleep.pressure")[int(released // 60) - 1]
    assert pressure_at_release > 0.8  # far above the normal evening peak
    assert any(
        s
        for t, s in zip(deprived.times(), deprived.column("motor.sleeping"), strict=True)
        if released <= t < released + 1800
    )
    assert not any(
        s
        for t, s in zip(control.times(), control.column("motor.sleeping"), strict=True)
        if released <= t < released + 1800
    )
