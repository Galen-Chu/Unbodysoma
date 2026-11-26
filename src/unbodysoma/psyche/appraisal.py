"""Appraisal: interpreting sensory input in light of the current bodily state."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax


class Appraisal(Module):
    """Estimates threat from exteroceptive cues, biased upward by vigilance.

    The bias is the minimal form of "the body colours perception": an
    already-vigilant organism (threatened, hurt, or running) reads the same
    cue as more threatening. The vigilance signal is norepinephrine
    (``neuro.norepinephrine``), which consolidates threat, pain and cardiac
    arousal — so a hurt organism over-perceives mild cues (hyper-vigilance).

    Learned expectation enters the same way as a perceptual cue: a cue that
    experience has paired with damage contributes its conditioned association
    (``psyche.conditioning.threat_expectation``) to appraised threat —
    conditioned fear, and its extinction, live here.
    """

    name = "psyche.appraisal"
    rate_hz = 10.0
    reads = (
        "extero.threat",
        "neuro.norepinephrine",
        "psyche.conditioning.threat_expectation",
        "psyche.attention.share_threat",
    )
    signal_specs = (SignalSpec("psyche.appraisal.threat", "normalized", 0.0, 1.0, "Appraised threat"),)
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "arousal_bias",
            0.5,
            "",
            0.0,
            5.0,
            "How much vigilance amplifies perceived threat (trait anxiety)",
        ),
        ParamSpec(
            "w_attention_gain",
            0.5,
            "",
            0.0,
            2.0,
            "Threat gain from attention: attended threats read larger, ignored ones smaller",
        ),
        ParamSpec(
            "w_learned_threat",
            1.0,
            "",
            0.0,
            5.0,
            "Appraised threat gained per unit of conditioned association",
        ),
        ParamSpec("tau", 0.5, "s", 0.01, 60.0, "Time constant of appraisal"),
    )
    state_fields = ("threat",)

    def __init__(
        self,
        arousal_bias: float = 0.5,
        w_attention_gain: float = 0.5,
        w_learned_threat: float = 1.0,
        tau: float = 0.5,
    ) -> None:
        self.arousal_bias = arousal_bias
        self.w_attention_gain = w_attention_gain
        self.w_learned_threat = w_learned_threat
        self.tau = tau
        self.threat = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("psyche.appraisal.threat", self.threat)

    def step(self, dt: float, port: BusPort) -> None:
        cue = port.read("extero.threat")
        attended = 1.0 + self.w_attention_gain * (port.read("psyche.attention.share_threat") - 1.0 / 6.0)
        learned = self.w_learned_threat * port.read("psyche.conditioning.threat_expectation")
        target = clamp(cue * attended * (1.0 + self.arousal_bias * port.read("neuro.norepinephrine")) + learned)
        self.threat = relax(self.threat, target, dt, self.tau)
        port.write("psyche.appraisal.threat", self.threat)
