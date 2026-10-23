"""Acceptance tests for water balance, thermoregulation and sheltering."""

from statistics import mean

import pytest

from unbodysoma import build_grid_human, build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import HealthMonitor, Recorder
from unbodysoma.world import Event, Hazard, Shelter, WaterSource

HOUR = 3600.0
WATER = Event(0.0, 1e9, "world.water_available", 1.0)
FOOD = Event(0.0, 1e9, "world.food_available", 1.0)


def scripted(events=(), ambient: float = 22.0, hydration: float = 0.9, seed: int = 0, **overrides) -> Engine:
    engine = build_minimal_human(
        events,
        seed=seed,
        overrides={
            "world.scripted": {"baselines": {"world.ambient_temperature": ambient}},
            "soma.fluid": {"initial_hydration": hydration},
            **overrides,
        },
    )
    return engine


def record(engine: Engine, keys, seconds: float, every: float = 10.0) -> dict:
    recorder = Recorder(keys, every=every)
    engine.observe(recorder)
    engine.run(seconds)
    return {"t": recorder.times(), **{k: recorder.column(k) for k in keys}}


# -- water ----------------------------------------------------------------------


def test_a_thirsty_organism_drinks_until_sated():
    rec = record(
        scripted([WATER], hydration=0.5), ["motor.drinking", "soma.fluid.hydration", "psyche.drive.thirst"], 1800
    )
    drinking = rec["motor.drinking"]
    assert max(drinking) == 1.0
    first, last = drinking.index(1.0), max(i for i, d in enumerate(drinking) if d == 1.0)
    assert all(drinking[first : last + 1])  # one continuous drink...
    assert drinking[-1] == 0.0  # ...that stopped once thirst was quenched
    assert rec["soma.fluid.hydration"][-1] > 0.75 > rec["soma.fluid.hydration"][0]
    assert rec["psyche.drive.thirst"][-1] < 0.1


def test_without_water_a_thirsty_organism_searches_and_dehydration_is_flagged():
    engine = scripted([FOOD], hydration=0.2)
    monitor = HealthMonitor().attach(engine)
    rec = record(engine, ["psyche.action.selected_seek_water", "motor.drinking"], 2 * HOUR)
    assert max(rec["motor.drinking"]) == 0.0
    assert mean(rec["psyche.action.selected_seek_water"][60:]) > 0.9  # spends its time looking for water
    assert "dehydration" in {a.rule for a in monitor.alerts if a.raised}


def test_osmolality_tracks_hydration_in_the_normal_range():
    engine = scripted(hydration=0.7)
    engine.step()
    assert engine.bus.read("soma.fluid.osmolality") == pytest.approx(285.0 + 40.0 * 0.3, abs=0.1)


def test_exertion_and_sweating_cost_water():
    def loss(**setup) -> float:
        engine = scripted(**setup.pop("world", {}))
        for key, value in setup.items():
            engine.clamp(key, value)
        engine.run(HOUR)
        return 0.9 - engine.bus.read("soma.fluid.hydration")

    rest = loss()
    assert loss(**{"motor.exertion": 0.8}) > 2.0 * rest
    assert loss(**{"soma.thermo.sweating": 0.5}) > 3.0 * rest


# -- heat -----------------------------------------------------------------------

THERMO = [
    "soma.thermo.core_temperature",
    "soma.thermo.shivering",
    "soma.thermo.sweating",
    "psyche.drive.thermal_discomfort",
]


def test_at_a_neutral_temperature_the_core_stays_at_37():
    rec = record(scripted([WATER, FOOD]), THERMO, 2 * HOUR, every=60.0)
    assert max(abs(t - 37.0) for t in rec["soma.thermo.core_temperature"]) < 0.05
    assert max(rec["soma.thermo.shivering"]) == 0.0 and max(rec["soma.thermo.sweating"]) == 0.0


def test_cold_makes_the_body_shiver_and_burn_energy():
    cold = scripted([WATER, FOOD], ambient=5.0)
    rec = record(cold, [*THERMO, "psyche.affect.valence"], 4 * HOUR, every=60.0)
    neutral = scripted([WATER, FOOD])
    neutral.run(4 * HOUR)
    core = rec["soma.thermo.core_temperature"]
    assert 35.5 < min(core) < 36.8  # cooled, but defended
    assert abs(core[-1] - core[-30]) < 0.05  # and settled
    assert rec["soma.thermo.shivering"][-1] > 0.3
    assert rec["psyche.drive.thermal_discomfort"][-1] > 0.3
    assert cold.bus.read("soma.metabolism.energy_reserve") < neutral.bus.read("soma.metabolism.energy_reserve")
    assert mean(rec["psyche.affect.valence"][-30:]) < 0.0


def test_heat_makes_the_body_sweat_and_lose_water():
    hot = scripted([FOOD], ambient=38.0)
    rec = record(hot, THERMO, 4 * HOUR, every=60.0)
    neutral = scripted([FOOD])
    neutral.run(4 * HOUR)
    assert 37.2 < max(rec["soma.thermo.core_temperature"]) < 38.5
    assert rec["soma.thermo.sweating"][-1] > 0.2
    assert hot.bus.read("soma.fluid.hydration") < neutral.bus.read("soma.fluid.hydration") - 0.05


# -- water and shelter in space ---------------------------------------------------


def grid(start_hour: float = 8.0, **world) -> Engine:
    overrides = {"world.grid": {"start_hour": start_hour}, "soma.circadian": {"start_hour": start_hour}}
    for key in ("fluid", "sleep"):
        if key in world:
            overrides[f"soma.{key}"] = world.pop(key)
    return build_grid_human(**{"food": (), "hazards": (), "water": (), "shelters": (), **world}, overrides=overrides)


def test_a_thirsty_organism_walks_to_water_it_can_see():
    engine = grid(water=[WaterSource(14.0, 10.0)], fluid={"initial_hydration": 0.5})
    rec = record(engine, ["motor.drinking", "world.position_x"], 600)
    assert max(rec["motor.drinking"]) == 1.0
    assert rec["world.position_x"][-1] == pytest.approx(14.0, abs=0.6)


def test_on_a_cold_night_the_organism_goes_to_its_shelter():
    engine = grid(start_hour=2.0, shelters=[Shelter(15.0, 10.0)])  # 02:00, about 7 °C outside
    rec = record(engine, ["world.in_shelter", "world.ambient_temperature", "soma.thermo.core_temperature"], 2 * HOUR)
    assert rec["world.ambient_temperature"][0] < 9.0
    arrived = rec["world.in_shelter"].index(1.0)
    assert rec["t"][arrived] < HOUR
    assert rec["world.ambient_temperature"][-1] > 15.0  # buffered inside
    core = rec["soma.thermo.core_temperature"]
    assert core[-1] > min(core) + 0.1  # warming up again


def test_hazards_cannot_reach_into_a_shelter():
    engine = grid(shelters=[Shelter(10.0, 10.0)], hazards=[Hazard(10.0, 10.0, radius=4.0)])
    rec = record(engine, ["world.threat", "psyche.action.selected_flee", "world.in_shelter"], 60, every=1.0)
    assert max(rec["world.threat"]) == 0.0
    assert max(rec["psyche.action.selected_flee"]) == 0.0
    assert min(rec["world.in_shelter"]) == 1.0


@pytest.mark.slow
def test_a_sleepy_organism_goes_home_to_sleep():
    engine = grid(start_hour=21.0, shelters=[Shelter(15.0, 10.0)], sleep={"initial_pressure": 0.6})
    rec = record(engine, ["motor.sleeping", "world.in_shelter"], 6 * HOUR)
    asleep = [inside for s, inside in zip(rec["motor.sleeping"], rec["world.in_shelter"], strict=True) if s]
    assert len(asleep) > 0.5 * len(rec["t"])  # slept most of the time...
    assert min(asleep) == 1.0  # ...and only inside the shelter
