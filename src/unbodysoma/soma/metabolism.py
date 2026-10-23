"""Energy metabolism — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax

_SECONDS_PER_HOUR = 3600.0


class Metabolism(Module):
    """A single lumped energy reserve plus a regulated blood glucose level.

    The reserve (fraction of full, 0..1) drains at a basal rate scaled up by
    exertion and is refilled by food intake. Glucose is held near its setpoint
    while the reserve lasts and is mobilized upward by adrenaline.
    """

    name = "soma.metabolism"
    rate_hz = 1.0
    reads = (
        "motor.exertion",
        "motor.sleeping",
        "world.food_intake",
        "soma.endocrine.adrenaline",
        "soma.thermo.shivering",
    )
    signal_specs = (
        SignalSpec("soma.metabolism.energy_reserve", "fraction", 0.0, 1.0, "Lumped energy store (1 = full)"),
        SignalSpec("soma.metabolism.glucose", "mg/dL", 0.0, 600.0, "Blood glucose"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("initial_reserve", 0.8, "fraction", 0.0, 1.0, "Energy reserve at t = 0"),
        ParamSpec(
            "hours_to_empty_at_rest",
            48.0,
            "h",
            1.0,
            500.0,
            "Time for a full reserve to drain at rest",
            source="calibrated: about three meals a day",
        ),
        ParamSpec("exertion_cost", 4.0, "", 0.0, 20.0, "Extra drain per unit exertion, relative to basal"),
        ParamSpec("shiver_cost", 3.0, "", 0.0, 20.0, "Extra drain per unit shivering, relative to basal"),
        ParamSpec("sleep_metabolic_factor", 0.9, "", 0.5, 1.0, "Basal drain during sleep, relative to awake rest"),
        ParamSpec("glucose_setpoint", 90.0, "mg/dL", 60.0, 130.0, "Defended fasting glucose"),
        ParamSpec("k_adrenaline", 40.0, "mg/dL", 0.0, 150.0, "Glucose mobilized per unit adrenaline"),
        ParamSpec("glucose_tau", 120.0, "s", 1.0, 3600.0, "Time constant of glucose regulation"),
        ParamSpec(
            "glucose_defense_reserve",
            0.1,
            "fraction",
            0.01,
            1.0,
            "Reserve below which glucose can no longer be defended",
        ),
    )
    state_fields = ("reserve", "glucose")

    def __init__(
        self,
        initial_reserve: float = 0.8,
        hours_to_empty_at_rest: float = 48.0,
        exertion_cost: float = 4.0,
        shiver_cost: float = 3.0,
        sleep_metabolic_factor: float = 0.9,
        glucose_setpoint: float = 90.0,
        k_adrenaline: float = 40.0,
        glucose_tau: float = 120.0,
        glucose_defense_reserve: float = 0.1,
    ) -> None:
        self.initial_reserve = initial_reserve
        self.hours_to_empty_at_rest = hours_to_empty_at_rest
        self.exertion_cost = exertion_cost
        self.shiver_cost = shiver_cost
        self.sleep_metabolic_factor = sleep_metabolic_factor
        self.glucose_setpoint = glucose_setpoint
        self.k_adrenaline = k_adrenaline
        self.glucose_tau = glucose_tau
        self.glucose_defense_reserve = glucose_defense_reserve
        self.reserve = initial_reserve
        self.glucose = glucose_setpoint

    def setup(self, port: BusPort) -> None:
        port.write("soma.metabolism.energy_reserve", self.reserve)
        port.write("soma.metabolism.glucose", self.glucose)

    def step(self, dt: float, port: BusPort) -> None:
        basal_drain = 1.0 / (self.hours_to_empty_at_rest * _SECONDS_PER_HOUR)
        if port.read("motor.sleeping") > 0.5:
            basal_drain *= self.sleep_metabolic_factor
        drain = basal_drain * (
            1.0
            + self.exertion_cost * port.read("motor.exertion")
            + self.shiver_cost * port.read("soma.thermo.shivering")
        )
        self.reserve = clamp(self.reserve + (port.read("world.food_intake") - drain) * dt)

        availability = min(1.0, self.reserve / self.glucose_defense_reserve)
        target = (self.glucose_setpoint + self.k_adrenaline * port.read("soma.endocrine.adrenaline")) * availability
        self.glucose = relax(self.glucose, target, dt, self.glucose_tau)

        port.write("soma.metabolism.energy_reserve", self.reserve)
        port.write("soma.metabolism.glucose", self.glucose)
