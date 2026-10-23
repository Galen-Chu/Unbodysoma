"""Homeostatic drives: felt urgency of bodily needs."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax

_CALIBRATED_SLEEP = "calibrated: 16 h wake / 8 h sleep, onset ≈ 23:00"


class Drives(Module):
    """Felt bodily needs: hunger, thirst, thermal discomfort and sleepiness.

    - hunger / thirst: thresholded, smoothed readings of interoceptive energy
      and water deficit, partly suppressed while asleep (a sleeping organism does
      not feel them as an awake one does; they return within ``tau`` of waking);
    - thermal discomfort: how far felt core temperature is from comfortable, in
      either direction (cold and heat both motivate seeking a better place);
    - sleepiness: where felt sleep pressure S sits between the two-process
      thresholds, ``(S - L) / (H - L)``, with ``H`` (sleep onset) and ``L``
      (waking) both shifted by the circadian signal C. It reaches 1 when S
      hits the onset threshold and 0 when S falls to the wake threshold;
      below that it turns negative (rested), which is what ends sleep.
      It is integrated over ``sleepiness_tau``: sleepiness is a slow state, and
      feeding raw sensory noise into the exponential switching hazards of
      action selection would make sleep end at random.
    """

    name = "psyche.drives"
    rate_hz = 2.0
    reads = (
        "intero.energy_deficit",
        "intero.water_deficit",
        "intero.thermal",
        "intero.sleep_pressure",
        "intero.circadian",
        "motor.sleeping",
    )
    signal_specs = (
        SignalSpec("psyche.drive.hunger", "normalized", 0.0, 1.0, "Felt urgency of eating"),
        SignalSpec("psyche.drive.thirst", "normalized", 0.0, 1.0, "Felt urgency of drinking"),
        SignalSpec("psyche.drive.thermal_discomfort", "normalized", 0.0, 1.0, "Felt cold or heat"),
        SignalSpec(
            "psyche.drive.sleepiness", "normalized", -1.0, 1.0, "Felt need for sleep (1 = sleep onset, 0 = wake point)"
        ),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("threshold", 0.2, "normalized", 0.0, 1.0, "Energy deficit below which no hunger is felt"),
        ParamSpec("span", 0.6, "normalized", 0.01, 1.0, "Deficit above threshold that is felt as maximal hunger"),
        ParamSpec("tau", 30.0, "s", 0.1, 3600.0, "Time constant of hunger and thirst"),
        ParamSpec("sleep_hunger_suppression", 0.5, "", 0.0, 1.0, "Share of felt hunger and thirst suppressed in sleep"),
        ParamSpec("thirst_threshold", 0.15, "normalized", 0.0, 1.0, "Water deficit below which no thirst is felt"),
        ParamSpec("thirst_span", 0.5, "normalized", 0.01, 1.0, "Deficit above threshold felt as maximal thirst"),
        ParamSpec(
            "thermal_deadband", 0.1, "normalized", 0.0, 1.0, "Felt temperature deviation that is still comfortable"
        ),
        ParamSpec(
            "thermal_span", 0.5, "normalized", 0.01, 1.0, "Deviation beyond the deadband felt as maximal discomfort"
        ),
        ParamSpec("thermal_tau", 60.0, "s", 0.1, 3600.0, "Time constant of thermal discomfort"),
        ParamSpec("sleepiness_tau", 300.0, "s", 1.0, 7200.0, "Time over which felt sleepiness is integrated"),
        ParamSpec(
            "sleep_onset_pressure",
            0.573,
            "normalized",
            0.0,
            1.0,
            "Mean upper threshold H0 of sleep pressure",
            source=_CALIBRATED_SLEEP,
        ),
        ParamSpec(
            "wake_pressure",
            0.193,
            "normalized",
            0.0,
            1.0,
            "Mean lower threshold L0 of sleep pressure",
            source=_CALIBRATED_SLEEP,
        ),
        ParamSpec(
            "circadian_amplitude",
            0.1,
            "normalized",
            0.0,
            0.5,
            "How far the circadian signal moves both thresholds",
            source=_CALIBRATED_SLEEP,
        ),
    )
    state_fields = ("hunger", "thirst", "discomfort", "felt_sleepiness")

    def __init__(
        self,
        threshold: float = 0.2,
        span: float = 0.6,
        tau: float = 30.0,
        sleep_hunger_suppression: float = 0.5,
        thirst_threshold: float = 0.15,
        thirst_span: float = 0.5,
        thermal_deadband: float = 0.1,
        thermal_span: float = 0.5,
        thermal_tau: float = 60.0,
        sleepiness_tau: float = 300.0,
        sleep_onset_pressure: float = 0.573,
        wake_pressure: float = 0.193,
        circadian_amplitude: float = 0.1,
    ) -> None:
        self.threshold = threshold
        self.span = span
        self.tau = tau
        self.sleep_hunger_suppression = sleep_hunger_suppression
        self.thirst_threshold = thirst_threshold
        self.thirst_span = thirst_span
        self.thermal_deadband = thermal_deadband
        self.thermal_span = thermal_span
        self.thermal_tau = thermal_tau
        self.sleepiness_tau = sleepiness_tau
        self.sleep_onset_pressure = sleep_onset_pressure
        self.wake_pressure = wake_pressure
        self.circadian_amplitude = circadian_amplitude
        self.hunger = 0.0
        self.thirst = 0.0
        self.discomfort = 0.0
        self.felt_sleepiness = 0.0

    def sleepiness(self, pressure: float, circadian: float) -> float:
        shift = self.circadian_amplitude * circadian
        upper, lower = self.sleep_onset_pressure + shift, self.wake_pressure + shift
        return clamp((pressure - lower) / (upper - lower), -1.0, 1.0)

    def _publish(self, port: BusPort) -> None:
        port.write("psyche.drive.hunger", self.hunger)
        port.write("psyche.drive.thirst", self.thirst)
        port.write("psyche.drive.thermal_discomfort", self.discomfort)
        port.write("psyche.drive.sleepiness", self.felt_sleepiness)

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    def step(self, dt: float, port: BusPort) -> None:
        awake = 1.0 - self.sleep_hunger_suppression * port.read("motor.sleeping")
        hunger = clamp((port.read("intero.energy_deficit") - self.threshold) / self.span) * awake
        thirst = clamp((port.read("intero.water_deficit") - self.thirst_threshold) / self.thirst_span) * awake
        discomfort = clamp((abs(port.read("intero.thermal")) - self.thermal_deadband) / self.thermal_span)
        sleepiness = self.sleepiness(port.read("intero.sleep_pressure"), port.read("intero.circadian"))
        self.hunger = relax(self.hunger, hunger, dt, self.tau)
        self.thirst = relax(self.thirst, thirst, dt, self.tau)
        self.discomfort = relax(self.discomfort, discomfort, dt, self.thermal_tau)
        self.felt_sleepiness = relax(self.felt_sleepiness, sleepiness, dt, self.sleepiness_tau)
        self._publish(port)
