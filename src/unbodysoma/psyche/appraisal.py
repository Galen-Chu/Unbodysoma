"""Appraisal: interpreting sensory input in light of the current bodily state."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax


class Appraisal(Module):
    """Estimates threat from exteroceptive cues, biased upward by current arousal.

    The arousal bias is the minimal form of "the body colours perception":
    an already-aroused organism reads the same cue as more threatening.
    """

    name = "psyche.appraisal"
    rate_hz = 10.0
    reads = ("extero.threat", "psyche.affect.arousal")
    signal_specs = (SignalSpec("psyche.appraisal.threat", "normalized", 0.0, 1.0, "Appraised threat"),)
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("arousal_bias", 0.5, "", 0.0, 5.0, "How much arousal amplifies perceived threat (trait anxiety)"),
        ParamSpec("tau", 0.5, "s", 0.01, 60.0, "Time constant of appraisal"),
    )
    state_fields = ("threat",)

    def __init__(self, arousal_bias: float = 0.5, tau: float = 0.5) -> None:
        self.arousal_bias = arousal_bias
        self.tau = tau
        self.threat = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("psyche.appraisal.threat", self.threat)

    def step(self, dt: float, port: BusPort) -> None:
        cue = port.read("extero.threat")
        target = clamp(cue * (1.0 + self.arousal_bias * port.read("psyche.affect.arousal")))
        self.threat = relax(self.threat, target, dt, self.tau)
        port.write("psyche.appraisal.threat", self.threat)
