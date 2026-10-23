"""Water: turning the organism's drinking behaviour into water intake."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec


class WaterIntake(Module):
    """Water enters the body only while water is available *and* the organism is drinking."""

    name = "world.water"
    rate_hz = 10.0
    reads = ("world.water_available", "motor.drinking")
    signal_specs = (
        SignalSpec(
            "world.water_intake", "fraction/s", 0.0, 1.0, "Water entering the body, as hydration fraction per second"
        ),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "intake_rate", 2e-3, "fraction/s", 0.0, 0.1, "Hydration restored per second of drinking (≈ 0.24 per 2 min)"
        ),
    )

    def __init__(self, intake_rate: float = 2e-3) -> None:
        self.intake_rate = intake_rate

    def setup(self, port: BusPort) -> None:
        port.write("world.water_intake", 0.0)

    def step(self, dt: float, port: BusPort) -> None:
        port.write(
            "world.water_intake", self.intake_rate * port.read("world.water_available") * port.read("motor.drinking")
        )
