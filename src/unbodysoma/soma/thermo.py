"""Thermoregulation — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

_SECONDS_PER_HOUR = 3600.0


class Thermoregulation(Module):
    """A lumped core temperature with autonomic defences.

    dT/dt = production − loss, in °C per hour:

    - production = basal · (1 + exertion_heat · exertion) + shiver_heat · shivering
    - loss       = conductance · (T − T_ambient) + sweat_cooling · sweating

    Shivering starts ``shiver_offset`` below the setpoint and costs energy
    (read by metabolism); sweating starts ``sweat_offset`` above it and costs
    water (read by fluid balance). At rest at 22 °C the body sits at 37 °C.
    """

    name = "soma.thermo"
    rate_hz = 1.0
    reads = ("world.ambient_temperature", "motor.exertion")
    signal_specs = (
        SignalSpec("soma.thermo.core_temperature", "°C", 30.0, 45.0, "Core body temperature"),
        SignalSpec(
            "soma.thermo.shivering", "normalized", 0.0, 1.0, "Shivering intensity (heat production, energy cost)"
        ),
        SignalSpec("soma.thermo.sweating", "normalized", 0.0, 1.0, "Sweating intensity (heat loss, water cost)"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("setpoint", 37.0, "°C", 35.0, 39.0, "Defended core temperature"),
        ParamSpec("initial_temperature", 37.0, "°C", 30.0, 45.0, "Core temperature at t = 0"),
        ParamSpec(
            "basal_heat",
            2.25,
            "°C/h",
            0.0,
            50.0,
            "Warming rate from resting metabolism",
            source="calibrated: 37 °C at 22 °C",
        ),
        ParamSpec("exertion_heat", 2.0, "", 0.0, 20.0, "Extra heat per unit exertion, relative to basal"),
        ParamSpec("conductance", 0.15, "1/h", 0.01, 10.0, "Heat loss per °C of core-to-ambient difference"),
        ParamSpec("shiver_heat", 4.0, "°C/h", 0.0, 50.0, "Warming rate at full shivering"),
        ParamSpec("sweat_cooling", 8.0, "°C/h", 0.0, 100.0, "Cooling rate at full sweating"),
        ParamSpec("shiver_offset", 0.3, "°C", 0.0, 3.0, "How far below the setpoint shivering starts"),
        ParamSpec("sweat_offset", 0.2, "°C", 0.0, 3.0, "How far above the setpoint sweating starts"),
        ParamSpec("response_span", 0.8, "°C", 0.05, 5.0, "Deviation beyond the onset at which a response is maximal"),
    )
    state_fields = ("temperature",)

    def __init__(
        self,
        setpoint: float = 37.0,
        initial_temperature: float = 37.0,
        basal_heat: float = 2.25,
        exertion_heat: float = 2.0,
        conductance: float = 0.15,
        shiver_heat: float = 4.0,
        sweat_cooling: float = 8.0,
        shiver_offset: float = 0.3,
        sweat_offset: float = 0.2,
        response_span: float = 0.8,
    ) -> None:
        self.setpoint = setpoint
        self.initial_temperature = initial_temperature
        self.basal_heat = basal_heat
        self.exertion_heat = exertion_heat
        self.conductance = conductance
        self.shiver_heat = shiver_heat
        self.sweat_cooling = sweat_cooling
        self.shiver_offset = shiver_offset
        self.sweat_offset = sweat_offset
        self.response_span = response_span
        self.temperature = initial_temperature

    def _responses(self) -> tuple[float, float]:
        shivering = clamp((self.setpoint - self.shiver_offset - self.temperature) / self.response_span)
        sweating = clamp((self.temperature - self.setpoint - self.sweat_offset) / self.response_span)
        return shivering, sweating

    def _publish(self, port: BusPort) -> None:
        shivering, sweating = self._responses()
        port.write("soma.thermo.core_temperature", self.temperature)
        port.write("soma.thermo.shivering", shivering)
        port.write("soma.thermo.sweating", sweating)

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    def step(self, dt: float, port: BusPort) -> None:
        shivering, sweating = self._responses()
        production = self.basal_heat * (1.0 + self.exertion_heat * port.read("motor.exertion"))
        production += self.shiver_heat * shivering
        loss = self.conductance * (self.temperature - port.read("world.ambient_temperature"))
        loss += self.sweat_cooling * sweating
        self.temperature = clamp(self.temperature + (production - loss) * dt / _SECONDS_PER_HOUR, 30.0, 45.0)
        self._publish(port)
