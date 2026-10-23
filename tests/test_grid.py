"""Acceptance tests for the grid world and navigation."""

import copy
import math
import random

import pytest

from unbodysoma import build_grid_human
from unbodysoma.core import BusPort, Engine, Module
from unbodysoma.observe import Recorder
from unbodysoma.world import FoodPatch, GridWorld, Hazard


class Motor(Module):
    """Drives the world with fixed motor commands, so the world alone is under test."""

    name = "test.motor"
    writes = ("motor.move_x", "motor.move_y", "motor.eating")

    def __init__(self, move_x: float = 0.0, move_y: float = 0.0, eating: float = 0.0) -> None:
        self.values = {"motor.move_x": move_x, "motor.move_y": move_y, "motor.eating": eating}

    def setup(self, port: BusPort) -> None:
        self.step(0.0, port)

    def step(self, dt: float, port: BusPort) -> None:
        for key, value in self.values.items():
            port.write(key, value)


def world_engine(world: GridWorld, **motor) -> Engine:
    engine = Engine(base_dt=0.05)
    engine.add(world)
    engine.add(Motor(**motor))
    return engine


def distance(world: GridWorld, x: float, y: float) -> float:
    return math.hypot(*world.offset(x, y))


# -- the world on its own ------------------------------------------------------


def test_edges_wrap_around():
    world = GridWorld(width=20.0, height=20.0, start=(1.0, 1.0))
    assert world.offset(19.0, 19.0) == pytest.approx((-2.0, -2.0))
    engine = world_engine(world, move_x=-1.0)
    engine.run(3.0)
    assert world.x == pytest.approx(18.0, abs=0.06)  # walked off the left edge, came in on the right


def test_movement_speed_is_capped():
    world = GridWorld(start=(5.0, 5.0), max_speed=1.0)
    world_engine(world, move_x=3.0, move_y=4.0).run(2.0)  # asks for 5x full speed
    assert distance(world, 5.0, 5.0) == pytest.approx(2.0, abs=0.06)


def test_patches_deplete_while_eaten_and_regrow():
    patch = FoodPatch(5.0, 5.0, capacity=1.0, regrow_per_hour=0.5)
    world = GridWorld(food=[patch], start=(5.0, 5.0), depletion_per_s=1 / 600)
    engine = world_engine(world, eating=1.0)
    engine.run(300.0)
    eaten = world.amounts[0]
    assert eaten == pytest.approx(1.0 - 300 / 600 + 0.5 * 300 / 3600, abs=0.01)
    assert engine.bus.read("world.food_available") == 1.0

    engine.run(3600.0)  # keeps "eating", but stops once the patch is nearly empty
    assert engine.bus.read("world.food_available") < 1.0
    regrowing = world_engine(GridWorld(food=[patch], start=(15.0, 15.0)))
    regrowing.modules[0].amounts = [0.2]
    regrowing.run(3600.0)
    assert regrowing.modules[0].amounts[0] == pytest.approx(0.7, abs=0.01)


def test_threat_fades_with_distance_and_points_to_the_hazard():
    hazard = Hazard(10.0, 10.0, radius=2.0, strength=0.9)
    engine = world_engine(GridWorld(hazards=[hazard], start=(11.0, 10.0)))
    engine.step()
    assert engine.bus.read("world.threat") == pytest.approx(0.45, abs=0.01)
    assert engine.bus.read("world.threat_dir_x") == pytest.approx(-1.0)
    far = world_engine(GridWorld(hazards=[hazard], start=(13.0, 10.0)))
    far.step()
    assert far.bus.read("world.threat") == 0.0


def test_recurring_hazards_repeat_their_window():
    daily = Hazard(10.0, 10.0, start=3600.0, end=7200.0, every=86400.0)
    assert [daily.active(h * 3600.0) for h in (0, 1, 1.5, 2, 24, 25, 25.5, 26, 49)] == [
        False,
        True,
        True,
        False,
        False,
        True,
        True,
        False,
        True,
    ]


def test_timed_hazards_are_only_present_in_their_window():
    hazard = Hazard(10.0, 10.0, radius=2.0, start=100.0, end=200.0)
    engine = world_engine(GridWorld(hazards=[hazard], start=(10.0, 10.0)))
    threat = Recorder(["world.threat"], every=50.0)
    engine.observe(threat)
    engine.run(250.0)
    assert threat.column("world.threat") == pytest.approx([0.0, 0.0, 0.9, 0.9, 0.0, 0.0])


# -- the organism in the world -------------------------------------------------


def organism(food=(), hazards=(), start=(10.0, 10.0), reserve: float = 0.8, seed: int = 0) -> Engine:
    return build_grid_human(
        food=food, hazards=hazards, start=start, seed=seed, overrides={"soma.metabolism": {"initial_reserve": reserve}}
    )


def test_a_hungry_organism_walks_to_food_it_can_see_and_eats():
    engine = organism(food=[FoodPatch(14.0, 10.0)], reserve=0.4)
    rec = Recorder(["motor.eating", "soma.metabolism.energy_reserve"], every=10.0)
    engine.observe(rec)
    engine.run(1200.0)
    world = engine.modules[0]
    assert distance(world, 14.0, 10.0) <= world.reach
    assert max(rec.column("motor.eating")) == 1.0
    assert rec.column("soma.metabolism.energy_reserve")[-1] > 0.45


def test_an_organism_runs_away_from_danger():
    hazard = Hazard(10.0, 10.0, radius=3.0, strength=0.9)
    engine = organism(hazards=[hazard], start=(11.0, 10.0))  # starts deep inside the danger zone
    engine.run(30.0)
    world = engine.modules[0]
    assert distance(world, 10.0, 10.0) > 2.0
    assert world.x > 11.0  # fled away from the hazard, not toward it


def test_a_hungry_organism_searches_for_food_beyond_its_senses():
    engine = organism(food=[FoodPatch(1.0, 10.0)], reserve=0.4)  # 9 cells away, senses reach 6
    rec = Recorder(["motor.eating"], every=10.0)
    engine.observe(rec)
    engine.run(2 * 3600.0)
    assert max(rec.column("motor.eating")) == 1.0


def test_a_sated_organism_stays_put():
    engine = organism(food=[FoodPatch(14.0, 10.0)], reserve=0.8)
    engine.run(600.0)
    assert distance(engine.modules[0], 10.0, 10.0) == pytest.approx(0.0, abs=1e-9)


def comparable(value):
    if isinstance(value, random.Random):
        return value.getstate()
    if isinstance(value, dict):
        return {k: comparable(v) for k, v in value.items()}
    return value


def test_grid_world_snapshots_cover_all_state():
    engine = organism(food=[FoodPatch(14.0, 10.0)], reserve=0.4)
    engine.run(200.0)
    snap = engine.snapshot()
    before = {m.name: comparable(copy.deepcopy(vars(m))) for m in engine.modules}
    engine.run(300.0)
    first = engine.bus.snapshot()
    engine.restore(snap)
    assert {m.name: comparable(vars(m)) for m in engine.modules} == before
    engine.run(300.0)
    assert engine.bus.snapshot() == first
