"""Water balance — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

_SECONDS_PER_HOUR = 3600.0


class FluidBalance(Module):
    """A lumped body-water reserve (1 = well hydrated, 0 = severely dehydrated).

    Water is lost continuously (urine, breath, skin), faster with exertion and
    sweating, slower in sleep, and replaced by drinking. Plasma osmolality is
    derived from the reserve so that the healthy range (≈ 285–295 mOsm/kg)
    corresponds to a well-hydrated body and thirst sets in near its top.
    """

    name = "soma.fluid"
    rate_hz = 1.0
    reads = ("motor.exertion", "motor.sleeping", "soma.thermo.sweating", "world.water_intake")
    signal_specs = (
        SignalSpec("soma.fluid.hydration", "fraction", 0.0, 1.0, "Body-water reserve (1 = well hydrated)"),
        SignalSpec("soma.fluid.osmolality", "mOsm/kg", 250.0, 350.0, "Plasma osmolality"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("initial_hydration", 0.9, "fraction", 0.0, 1.0, "Hydration at t = 0"),
        ParamSpec(
            "hours_to_empty_at_rest",
            48.0,
            "h",
            1.0,
            500.0,
            "Time for a full reserve to be lost at rest without drinking",
            source="calibrated: a few drinks a day",
        ),
        ParamSpec("exertion_cost", 2.0, "", 0.0, 20.0, "Extra loss per unit exertion, relative to basal"),
        ParamSpec("sweat_cost", 6.0, "", 0.0, 50.0, "Extra loss per unit sweating, relative to basal"),
        ParamSpec("sleep_loss_factor", 0.8, "", 0.3, 1.0, "Basal loss during sleep, relative to awake rest"),
        ParamSpec(
            "osmolality_at_full",
            285.0,
            "mOsm/kg",
            250.0,
            320.0,
            "Osmolality when fully hydrated",
            source="L0 mapping onto the normal range",
        ),
        ParamSpec(
            "osmolality_span",
            40.0,
            "mOsm/kg",
            1.0,
            100.0,
            "Osmolality rise from full to empty reserve",
            source="L0 mapping onto the normal range",
        ),
    )
    state_fields = ("hydration",)

    def __init__(
        self,
        initial_hydration: float = 0.9,
        hours_to_empty_at_rest: float = 48.0,
        exertion_cost: float = 2.0,
        sweat_cost: float = 6.0,
        sleep_loss_factor: float = 0.8,
        osmolality_at_full: float = 285.0,
        osmolality_span: float = 40.0,
    ) -> None:
        self.initial_hydration = initial_hydration
        self.hours_to_empty_at_rest = hours_to_empty_at_rest
        self.exertion_cost = exertion_cost
        self.sweat_cost = sweat_cost
        self.sleep_loss_factor = sleep_loss_factor
        self.osmolality_at_full = osmolality_at_full
        self.osmolality_span = osmolality_span
        self.hydration = initial_hydration

    def _publish(self, port: BusPort) -> None:
        port.write("soma.fluid.hydration", self.hydration)
        port.write("soma.fluid.osmolality", self.osmolality_at_full + self.osmolality_span * (1.0 - self.hydration))

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    def step(self, dt: float, port: BusPort) -> None:
        basal = 1.0 / (self.hours_to_empty_at_rest * _SECONDS_PER_HOUR)
        if port.read("motor.sleeping") > 0.5:
            basal *= self.sleep_loss_factor
        loss = basal * (
            1.0 + self.exertion_cost * port.read("motor.exertion") + self.sweat_cost * port.read("soma.thermo.sweating")
        )
        self.hydration = clamp(self.hydration + (port.read("world.water_intake") - loss) * dt)
        self._publish(port)
