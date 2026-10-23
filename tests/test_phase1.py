"""Phase 1 completion: three days of autonomous life in the grid world (docs/ROADMAP.md).

Runs scenarios/grid_72h.toml end to end (about 1-2 minutes) and checks the
completion criteria: consolidated nightly sleep, regular meals from more than one
patch, flight from predators, little time in danger, and a healthy body.
"""

import math
from pathlib import Path

import pytest

from unbodysoma.config import load_scenario
from unbodysoma.observe import HealthMonitor, Recorder
from unbodysoma.observe.behavior import episodes, per_day, time_fraction

pytestmark = pytest.mark.slow

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "grid_72h.toml"
KEYS = (
    "motor.sleeping",
    "motor.eating",
    "psyche.action.selected_flee",
    "world.threat",
    "world.position_x",
    "world.position_y",
    "soma.metabolism.energy_reserve",
    "soma.circadian.clock_hour",
)


@pytest.fixture(scope="module")
def life():
    scenario = load_scenario(SCENARIO)
    engine = scenario.build()
    monitor = HealthMonitor(every=10.0, halt_on="critical").attach(engine)
    recorder = Recorder(KEYS, every=1.0)
    engine.observe(recorder)
    stopped = engine.run(scenario.duration_s)
    columns = {k: recorder.column(k) for k in KEYS}
    return {"engine": engine, "monitor": monitor, "stopped": stopped, "t": recorder.times(), **columns}


def clock(life, t: float) -> float:
    return life["soma.circadian.clock_hour"][int(round(t))]


def test_the_organism_survives_three_days_healthy(life):
    assert life["stopped"] is None
    assert [a.rule for a in life["monitor"].alerts if a.raised] == []
    assert 0.3 < min(life["soma.metabolism.energy_reserve"]) and max(life["soma.metabolism.energy_reserve"]) <= 0.85


def test_it_sleeps_once_every_night(life):
    sleeps = episodes(life["t"], life["motor.sleeping"])
    assert len(sleeps) == 3
    for s in sleeps:
        assert 21.0 <= clock(life, s.start) <= 24.0
        assert 6.5 * 3600 <= s.duration <= 9.0 * 3600


def test_it_eats_regular_meals_from_more_than_one_patch(life):
    meals = episodes(life["t"], life["motor.eating"])
    assert len(meals) >= 8
    assert all(n >= 3 for n in per_day(meals, 3)[1:])  # day 1 starts well fed
    world = life["engine"].modules[0]

    def torus_distance(patch, x: float, y: float) -> float:
        dx = (patch.x - x + world.width / 2) % world.width - world.width / 2
        dy = (patch.y - y + world.height / 2) % world.height - world.height / 2
        return math.hypot(dx, dy)

    used = set()
    for m in meals:
        x, y = life["world.position_x"][int(m.start)], life["world.position_y"][int(m.start)]
        used.add(min(world.food, key=lambda patch: torus_distance(patch, x, y)))
    assert len(used) >= 2


def test_it_flees_from_predators_and_stays_out_of_danger(life):
    flights = episodes(life["t"], life["psyche.action.selected_flee"])
    assert len(flights) >= 1
    for f in flights:
        window = life["world.threat"][int(f.start) - 5 : int(f.start) + 1]
        assert max(window) > 0.3  # every flight was a response to real danger
    assert time_fraction(life["world.threat"], 0.6) < 0.005
