"""Core affect on the valence / arousal plane (Russell's circumplex)."""

from __future__ import annotations

from ..core import BusPort, Module, clamp, relax


class Affect(Module):
    """Integrates interoceptive arousal, appraised threat and unmet drives.

    - arousal in [0, 1]: mostly felt bodily activation, partly appraised threat
    - valence in [-1, 1]: pulled down by threat and by homeostatic need
    """

    name = "psyche.affect"
    rate_hz = 10.0
    reads = ("intero.cardiac_arousal", "psyche.appraisal.threat", "psyche.drive.hunger")
    writes = ("psyche.affect.valence", "psyche.affect.arousal")

    def __init__(self, baseline_valence: float = 0.1, tau: float = 2.0) -> None:
        self.baseline_valence = baseline_valence
        self.tau = tau
        self.valence = baseline_valence
        self.arousal = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("psyche.affect.valence", self.valence)
        port.write("psyche.affect.arousal", self.arousal)

    def step(self, dt: float, port: BusPort) -> None:
        threat = port.read("psyche.appraisal.threat")
        hunger = port.read("psyche.drive.hunger")
        arousal_target = clamp(0.6 * port.read("intero.cardiac_arousal") + 0.4 * threat)
        valence_target = clamp(self.baseline_valence - 0.9 * threat - 0.5 * hunger, -1.0, 1.0)
        self.arousal = relax(self.arousal, arousal_target, dt, self.tau)
        self.valence = relax(self.valence, valence_target, dt, self.tau)
        port.write("psyche.affect.valence", self.valence)
        port.write("psyche.affect.arousal", self.arousal)
