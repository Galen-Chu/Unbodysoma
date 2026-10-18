"""Energy metabolism — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

from ..core import BusPort, Module, clamp, relax

_SECONDS_PER_HOUR = 3600.0


class Metabolism(Module):
    """A single lumped energy reserve plus a regulated blood glucose level.

    The reserve (fraction of full, 0..1) drains at a basal rate scaled up by
    exertion and is refilled by food intake. Glucose is held near its setpoint
    while the reserve lasts and is mobilized upward by adrenaline.
    """

    name = "soma.metabolism"
    rate_hz = 1.0
    reads = ("motor.exertion", "world.food_intake", "soma.endocrine.adrenaline")
    writes = ("soma.metabolism.energy_reserve", "soma.metabolism.glucose")
    state_fields = ("reserve", "glucose")

    def __init__(
        self,
        initial_reserve: float = 0.8,
        hours_to_empty_at_rest: float = 16.0,
        exertion_cost: float = 4.0,
        glucose_setpoint: float = 90.0,
        k_adrenaline: float = 40.0,
        glucose_tau: float = 120.0,
    ) -> None:
        self.basal_drain = 1.0 / (hours_to_empty_at_rest * _SECONDS_PER_HOUR)
        self.exertion_cost = exertion_cost
        self.glucose_setpoint = glucose_setpoint
        self.k_adrenaline = k_adrenaline
        self.glucose_tau = glucose_tau
        self.reserve = initial_reserve
        self.glucose = glucose_setpoint

    def setup(self, port: BusPort) -> None:
        port.write("soma.metabolism.energy_reserve", self.reserve)
        port.write("soma.metabolism.glucose", self.glucose)

    def step(self, dt: float, port: BusPort) -> None:
        exertion = port.read("motor.exertion")
        drain = self.basal_drain * (1.0 + self.exertion_cost * exertion)
        self.reserve = clamp(self.reserve + (port.read("world.food_intake") - drain) * dt)

        # Below 10 % reserve the body can no longer defend the glucose setpoint.
        availability = min(1.0, self.reserve / 0.1)
        target = (self.glucose_setpoint + self.k_adrenaline * port.read("soma.endocrine.adrenaline")) * availability
        self.glucose = relax(self.glucose, target, dt, self.glucose_tau)

        port.write("soma.metabolism.energy_reserve", self.reserve)
        port.write("soma.metabolism.glucose", self.glucose)
