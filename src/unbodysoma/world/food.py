"""Food: turning the organism's eating behaviour into energy intake."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec


class FoodSource(Module):
    """Energy enters the body only while food is available *and* the organism is eating.

    This is the world's side of the feeding loop: availability is part of the
    environment, eating is a motor command, intake is their physical result.
    """

    name = "world.food"
    rate_hz = 10.0
    reads = ("world.food_available", "motor.eating")
    signal_specs = (
        SignalSpec(
            "world.food_intake", "fraction/s", 0.0, 1.0, "Energy entering the body, as reserve fraction per second"
        ),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "intake_rate", 3e-4, "fraction/s", 0.0, 0.01, "Reserve refilled per second of eating (≈ 0.3 per 15 min)"
        ),
    )

    def __init__(self, intake_rate: float = 3e-4) -> None:
        self.intake_rate = intake_rate

    def setup(self, port: BusPort) -> None:
        port.write("world.food_intake", 0.0)

    def step(self, dt: float, port: BusPort) -> None:
        intake = self.intake_rate * port.read("world.food_available") * port.read("motor.eating")
        port.write("world.food_intake", intake)
