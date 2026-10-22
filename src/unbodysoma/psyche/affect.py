"""Core affect on the valence / arousal plane (Russell's circumplex)."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax


class Affect(Module):
    """Integrates interoceptive arousal, appraised threat and unmet drives.

    - arousal in [0, 1]: mostly felt bodily activation, partly appraised threat
    - valence in [-1, 1]: pulled down by threat and by homeostatic need
    """

    name = "psyche.affect"
    rate_hz = 10.0
    reads = ("intero.cardiac_arousal", "psyche.appraisal.threat", "psyche.drive.hunger")
    signal_specs = (
        SignalSpec("psyche.affect.valence", "normalized", -1.0, 1.0, "Core affect: pleasant (+) vs unpleasant (-)"),
        SignalSpec("psyche.affect.arousal", "normalized", 0.0, 1.0, "Core affect: activation"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("baseline_valence", 0.1, "normalized", -1.0, 1.0, "Valence with no threat or need (trait affect)"),
        ParamSpec("w_cardiac_arousal", 0.6, "", 0.0, 1.0, "Weight of felt cardiac activation in arousal"),
        ParamSpec("w_threat_arousal", 0.4, "", 0.0, 1.0, "Weight of appraised threat in arousal"),
        ParamSpec("w_threat_valence", 0.9, "", 0.0, 2.0, "Valence lost per unit appraised threat"),
        ParamSpec("w_hunger_valence", 0.5, "", 0.0, 2.0, "Valence lost per unit hunger"),
        ParamSpec("tau", 2.0, "s", 0.01, 600.0, "Time constant of affect"),
    )
    state_fields = ("valence", "arousal")

    def __init__(
        self,
        baseline_valence: float = 0.1,
        w_cardiac_arousal: float = 0.6,
        w_threat_arousal: float = 0.4,
        w_threat_valence: float = 0.9,
        w_hunger_valence: float = 0.5,
        tau: float = 2.0,
    ) -> None:
        self.baseline_valence = baseline_valence
        self.w_cardiac_arousal = w_cardiac_arousal
        self.w_threat_arousal = w_threat_arousal
        self.w_threat_valence = w_threat_valence
        self.w_hunger_valence = w_hunger_valence
        self.tau = tau
        self.valence = baseline_valence
        self.arousal = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("psyche.affect.valence", self.valence)
        port.write("psyche.affect.arousal", self.arousal)

    def step(self, dt: float, port: BusPort) -> None:
        threat = port.read("psyche.appraisal.threat")
        hunger = port.read("psyche.drive.hunger")
        arousal_target = clamp(
            self.w_cardiac_arousal * port.read("intero.cardiac_arousal") + self.w_threat_arousal * threat
        )
        valence_target = clamp(
            self.baseline_valence - self.w_threat_valence * threat - self.w_hunger_valence * hunger, -1.0, 1.0
        )
        self.arousal = relax(self.arousal, arousal_target, dt, self.tau)
        self.valence = relax(self.valence, valence_target, dt, self.tau)
        port.write("psyche.affect.valence", self.valence)
        port.write("psyche.affect.arousal", self.arousal)
