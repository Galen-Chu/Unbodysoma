"""Phase 1 completion: three days of autonomous life in the grid world (docs/ROADMAP.md).

Runs scenarios/grid_72h.toml end to end (about 2-3 minutes) and checks the
completion criteria: consolidated nightly sleep at home, regular meals from more
than one patch, regular drinking, a defended body temperature in a day-night
climate, flight from predators, little time in danger, and a healthy body.
"""

import math
from pathlib import Path
from statistics import mean

import pytest

from unbodysoma.config import load_scenario
from unbodysoma.observe import HealthMonitor, Recorder
from unbodysoma.observe.behavior import episodes, per_day, time_fraction

pytestmark = pytest.mark.slow

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "grid_72h.toml"
KEYS = (
    "motor.sleeping",
    "motor.eating",
    "motor.drinking",
    "psyche.action.selected_flee",
    "psyche.affect.valence",
    "world.threat",
    "world.in_shelter",
    "world.position_x",
    "world.position_y",
    "world.outside_temperature",
    "soma.metabolism.energy_reserve",
    "soma.fluid.hydration",
    "soma.thermo.core_temperature",
    "soma.circadian.clock_hour",
)
# Prolonged strongly negative valence is not a physiological failure but must stay
# visible (docs/ETHICS.md §3); it is checked separately below.
AFFECTIVE_RULES = {"prolonged_negative_valence"}


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
    physiological = [a.rule for a in life["monitor"].alerts if a.raised and a.rule not in AFFECTIVE_RULES]
    assert physiological == []
    assert 0.3 < min(life["soma.metabolism.energy_reserve"]) and max(life["soma.metabolism.energy_reserve"]) <= 0.85
    assert min(life["soma.fluid.hydration"]) > 0.4


def test_strongly_negative_states_are_rare(life):
    assert time_fraction([-v for v in life["psyche.affect.valence"]], 0.5) < 0.02


def test_it_sleeps_once_every_night_at_home(life):
    sleeps = episodes(life["t"], life["motor.sleeping"])
    assert len(sleeps) == 3
    for s in sleeps:
        assert 21.0 <= clock(life, s.start) <= 24.0
        assert 6.5 * 3600 <= s.duration <= 9.0 * 3600
    at_home = [home for asleep, home in zip(life["motor.sleeping"], life["world.in_shelter"], strict=True) if asleep]
    assert mean(at_home) > 0.95


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


def test_it_drinks_every_day(life):
    drinks = episodes(life["t"], life["motor.drinking"])
    assert all(n >= 1 for n in per_day(drinks, 3))
    assert len(drinks) >= 4


def test_it_defends_its_temperature_through_cold_nights(life):
    assert min(life["world.outside_temperature"]) < 10.0 < 20.0 < max(life["world.outside_temperature"])
    core = life["soma.thermo.core_temperature"]
    assert 36.0 < min(core) and max(core) < 38.0


def test_it_flees_from_predators_and_stays_out_of_danger(life):
    flights = episodes(life["t"], life["psyche.action.selected_flee"])
    assert len(flights) >= 1
    for f in flights:
        window = life["world.threat"][int(f.start) - 5 : int(f.start) + 1]
        assert max(window) > 0.3  # every flight was a response to real danger
    assert time_fraction(life["world.threat"], 0.6) < 0.005
