"""Place memory: where it hurt stays dangerous, steering avoids it (Phase 4).

The spatial loop of Phase 4: pain deposits danger at the organism's
position, the danger field decays over days, and navigation bends
goal-directed movement away from nearby danger. Anchored on learned place
avoidance and the cognitive-map lineage (O'Keefe & Nadel, 1978). Acceptance
below; equations: docs/PSYCHE.md §4.10.
"""

from math import hypot

import pytest

from unbodysoma import build_grid_human
from unbodysoma.core import BusPort, Engine, SignalBus
from unbodysoma.observe import Recorder
from unbodysoma.psyche import PlaceMemory
from unbodysoma.world import FoodPatch, Hazard, Shelter, WaterSource

DANGER = "psyche.place_memory.danger"
AVOID_X = "psyche.place_memory.avoid_x"
AVOID_Y = "psyche.place_memory.avoid_y"
POSITIONS = ("world.position_x", "world.position_y")


class _Bench:
    """Drives the module directly with a scripted position and pain."""

    def __init__(self, **params) -> None:
        self.bus = SignalBus()
        self.mod = PlaceMemory(**params)
        self.module_port = BusPort(self.bus, self.mod.name, self.mod.writes)
        self.stim = BusPort(self.bus, "bench", POSITIONS + ("intero.pain",))
        self.bus.commit()

    def run(self, x: float, y: float, pain: float, seconds: float, dt: float = 0.1) -> None:
        for i in range(round(seconds / dt)):
            self.stim.write("world.position_x", x)
            self.stim.write("world.position_y", y)
            self.stim.write("intero.pain", pain)
            self.bus.commit()
            self.module_port.time = (i + 1) * dt
            self.mod.step(dt, self.module_port)
            self.bus.commit()


def test_pain_marks_the_place():
    bench = _Bench()
    bench.run(5.0, 5.0, pain=1.0, seconds=60.0)
    assert bench.mod.danger[5 * 20 + 5] > 0.5  # the cell remembers


def test_repulsion_points_away():
    bench = _Bench()
    bench.run(5.0, 5.0, pain=1.0, seconds=60.0)
    bench.run(5.0, 7.0, pain=0.0, seconds=1.0)
    ay = bench.bus.read(AVOID_Y)
    assert ay > 0.2  # pushed away from the danger to the south
    assert abs(bench.bus.read(AVOID_X)) < ay  # mostly perpendicular-away, not sideways


def test_danger_decays_over_days():
    bench = _Bench(tau_danger=600.0)
    bench.run(5.0, 5.0, pain=1.0, seconds=60.0)
    hot = bench.mod.danger[5 * 20 + 5]
    bench.run(5.0, 5.0, pain=0.0, seconds=600.0)
    assert bench.mod.danger[5 * 20 + 5] < 0.5 * hot


def _choosing_engine(lesioned: bool) -> Engine:
    """Two symmetric rich patches; the north-west one sits in a hazard that
    hurts whoever feeds there. Everything else is equidistant and neutral."""
    engine: Engine = build_grid_human(
        food=(FoodPatch(6.0, 6.0, regrow_per_hour=0.8), FoodPatch(14.0, 14.0, regrow_per_hour=0.8)),
        hazards=(Hazard(6.0, 6.0, radius=2.5, strength=0.5),),
        water=(WaterSource(10.0, 10.0),),
        shelters=(Shelter(10.0, 10.0),),
        start=(10.0, 10.0),
        seed=0,
        overrides={"soma.metabolism": {"initial_reserve": 0.4}},
    )
    if lesioned:
        engine.lesion("psyche.place_memory", 0.0, 1e9)
    return engine


@pytest.mark.slow
def test_it_learns_to_feed_where_it_does_not_hurt():
    """Same world, same seed, one and a half days: with place memory the
    organism shifts its meals to the safe patch; its amnesic twin keeps
    feeding wherever the food is."""

    def run_world(lesioned: bool) -> Recorder:
        engine = _choosing_engine(lesioned)
        rec = Recorder((*POSITIONS, DANGER, "intero.pain", "motor.eating"), every=10.0)
        engine.observe(rec)
        engine.run(1.5 * 86400.0)
        return rec

    normal = run_world(False)
    amnesic = run_world(True)

    def feeding_share_near(rec: Recorder, x: float, y: float) -> float:
        eating = [
            hypot(px - x, py - y) < 2.5
            for px, py, e in zip(
                rec.column("world.position_x"), rec.column("world.position_y"), rec.column("motor.eating"), strict=True
            )
            if e > 0.5
        ]
        return sum(eating) / len(eating)

    assert max(normal.column(DANGER)) > 0.5  # the north-west patch is remembered as dangerous
    assert feeding_share_near(amnesic, 6.0, 6.0) > 0.3  # the amnesic twin still feeds there
    assert feeding_share_near(normal, 6.0, 6.0) < 0.6 * feeding_share_near(amnesic, 6.0, 6.0)  # it shifted away
