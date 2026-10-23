"""Homeostatic drives: felt urgency of bodily needs."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax


class Drives(Module):
    """Felt bodily needs: hunger and sleepiness.

    - hunger: a thresholded, smoothed reading of interoceptive energy deficit,
      partly suppressed while asleep (a sleeping organism does not feel hunger
      as an awake one does; it returns within ``tau`` of waking);
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
    reads = ("intero.energy_deficit", "intero.sleep_pressure", "intero.circadian", "motor.sleeping")
    signal_specs = (
        SignalSpec("psyche.drive.hunger", "normalized", 0.0, 1.0, "Felt urgency of eating"),
        SignalSpec(
            "psyche.drive.sleepiness", "normalized", -1.0, 1.0, "Felt need for sleep (1 = sleep onset, 0 = wake point)"
        ),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("threshold", 0.2, "normalized", 0.0, 1.0, "Energy deficit below which no hunger is felt"),
        ParamSpec("span", 0.6, "normalized", 0.01, 1.0, "Deficit above threshold that is felt as maximal hunger"),
        ParamSpec("tau", 30.0, "s", 0.1, 3600.0, "Time constant of hunger"),
        ParamSpec("sleep_hunger_suppression", 0.5, "", 0.0, 1.0, "Share of felt hunger suppressed during sleep"),
        ParamSpec("sleepiness_tau", 300.0, "s", 1.0, 7200.0, "Time over which felt sleepiness is integrated"),
        ParamSpec(
            "sleep_onset_pressure",
            0.573,
            "normalized",
            0.0,
            1.0,
            "Mean upper threshold H0 of sleep pressure",
            source="calibrated: 16 h wake / 8 h sleep, onset ≈ 23:00",
        ),
        ParamSpec(
            "wake_pressure",
            0.193,
            "normalized",
            0.0,
            1.0,
            "Mean lower threshold L0 of sleep pressure",
            source="calibrated: 16 h wake / 8 h sleep, onset ≈ 23:00",
        ),
        ParamSpec(
            "circadian_amplitude",
            0.1,
            "normalized",
            0.0,
            0.5,
            "How far the circadian signal moves both thresholds",
            source="calibrated: 16 h wake / 8 h sleep, onset ≈ 23:00",
        ),
    )
    state_fields = ("hunger", "felt_sleepiness")

    def __init__(
        self,
        threshold: float = 0.2,
        span: float = 0.6,
        tau: float = 30.0,
        sleep_hunger_suppression: float = 0.5,
        sleepiness_tau: float = 300.0,
        sleep_onset_pressure: float = 0.573,
        wake_pressure: float = 0.193,
        circadian_amplitude: float = 0.1,
    ) -> None:
        self.threshold = threshold
        self.span = span
        self.tau = tau
        self.sleep_hunger_suppression = sleep_hunger_suppression
        self.sleepiness_tau = sleepiness_tau
        self.sleep_onset_pressure = sleep_onset_pressure
        self.wake_pressure = wake_pressure
        self.circadian_amplitude = circadian_amplitude
        self.hunger = 0.0
        self.felt_sleepiness = 0.0

    def sleepiness(self, pressure: float, circadian: float) -> float:
        shift = self.circadian_amplitude * circadian
        upper, lower = self.sleep_onset_pressure + shift, self.wake_pressure + shift
        return clamp((pressure - lower) / (upper - lower), -1.0, 1.0)

    def setup(self, port: BusPort) -> None:
        port.write("psyche.drive.hunger", self.hunger)
        port.write("psyche.drive.sleepiness", self.felt_sleepiness)

    def step(self, dt: float, port: BusPort) -> None:
        target = clamp((port.read("intero.energy_deficit") - self.threshold) / self.span)
        target *= 1.0 - self.sleep_hunger_suppression * port.read("motor.sleeping")
        self.hunger = relax(self.hunger, target, dt, self.tau)
        port.write("psyche.drive.hunger", self.hunger)
        sleepiness = self.sleepiness(port.read("intero.sleep_pressure"), port.read("intero.circadian"))
        self.felt_sleepiness = relax(self.felt_sleepiness, sleepiness, dt, self.sleepiness_tau)
        port.write("psyche.drive.sleepiness", self.felt_sleepiness)
