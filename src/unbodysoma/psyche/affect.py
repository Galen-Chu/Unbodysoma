"""Core affect on the valence / arousal plane (Russell's circumplex)."""

from __future__ import annotations

import math
import random

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, ou_step, relax


class Affect(Module):
    """Integrates interoceptive arousal, appraised threat and unmet drives.

    - arousal in [0, 1]: mostly felt bodily activation, partly appraised threat
    - valence in [-1, 1]: pulled down by threat and by homeostatic need

    Both drift slowly on their own (Ornstein-Uhlenbeck fluctuation of the
    targets), so mood is never perfectly flat even when nothing happens.
    """

    name = "psyche.affect"
    rate_hz = 10.0
    reads = (
        "intero.cardiac_arousal",
        "intero.pain",
        "neuro.dopamine",
        "neuro.serotonin",
        "psyche.habituation.novelty",
        "psyche.appraisal.threat",
        "psyche.drive.hunger",
        "psyche.drive.thirst",
        "psyche.drive.thermal_discomfort",
    )
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
        ParamSpec("w_thirst_valence", 0.5, "", 0.0, 2.0, "Valence lost per unit thirst"),
        ParamSpec("w_thermal_valence", 0.4, "", 0.0, 2.0, "Valence lost per unit thermal discomfort"),
        ParamSpec("w_pain_valence", 1.2, "", 0.0, 2.0, "Valence lost per unit felt pain"),
        ParamSpec("w_pain_arousal", 0.3, "", 0.0, 1.0, "Arousal gained per unit felt pain"),
        ParamSpec("w_dopamine_valence", 0.1, "", 0.0, 1.0, "Valence gained per unit dopamine (relief feels good)"),
        ParamSpec(
            "w_serotonin_valence",
            0.4,
            "",
            0.0,
            2.0,
            "Valence shift per unit serotonin tone above/below 0.5 (slow mood)",
        ),
        ParamSpec("w_novelty_arousal", 0.15, "", 0.0, 1.0, "Arousal gained per unit felt novelty (orienting response)"),
        ParamSpec(
            "need_saturation",
            1.0,
            "",
            0.0,
            1.0,
            "Blend of multi-need valence pooling: 0 = linear sum, 1 = saturating union",
            source="decided by behavioral data, 2026-11-16 (docs/PSYCHE.md §5)",
        ),
        ParamSpec("tau", 2.0, "s", 0.01, 600.0, "Time constant of affect"),
        ParamSpec("valence_sigma", 0.03, "normalized", 0.0, 0.5, "SD of spontaneous valence fluctuation"),
        ParamSpec("arousal_sigma", 0.02, "normalized", 0.0, 0.5, "SD of spontaneous arousal fluctuation"),
        ParamSpec("fluctuation_tau", 60.0, "s", 1.0, 36000.0, "Correlation time of spontaneous fluctuation"),
        ParamSpec("seed", 3, "", 0, math.inf, "Random seed of the fluctuation", source="run setting"),
    )
    state_fields = ("valence", "arousal", "valence_drift", "arousal_drift", "_rng")

    def __init__(
        self,
        baseline_valence: float = 0.1,
        w_cardiac_arousal: float = 0.6,
        w_threat_arousal: float = 0.4,
        w_threat_valence: float = 0.9,
        w_hunger_valence: float = 0.5,
        w_thirst_valence: float = 0.5,
        w_thermal_valence: float = 0.4,
        w_pain_valence: float = 1.2,
        w_pain_arousal: float = 0.3,
        w_dopamine_valence: float = 0.1,
        w_serotonin_valence: float = 0.4,
        w_novelty_arousal: float = 0.15,
        need_saturation: float = 1.0,
        tau: float = 2.0,
        valence_sigma: float = 0.03,
        arousal_sigma: float = 0.02,
        fluctuation_tau: float = 60.0,
        seed: int = 3,
    ) -> None:
        self.baseline_valence = baseline_valence
        self.w_cardiac_arousal = w_cardiac_arousal
        self.w_threat_arousal = w_threat_arousal
        self.w_threat_valence = w_threat_valence
        self.w_hunger_valence = w_hunger_valence
        self.w_thirst_valence = w_thirst_valence
        self.w_thermal_valence = w_thermal_valence
        self.w_pain_valence = w_pain_valence
        self.w_pain_arousal = w_pain_arousal
        self.w_dopamine_valence = w_dopamine_valence
        self.w_serotonin_valence = w_serotonin_valence
        self.w_novelty_arousal = w_novelty_arousal
        self.need_saturation = need_saturation
        self.tau = tau
        self.valence_sigma = valence_sigma
        self.arousal_sigma = arousal_sigma
        self.fluctuation_tau = fluctuation_tau
        self.seed = seed
        self._rng = random.Random(seed)
        self.valence = baseline_valence
        self.arousal = 0.0
        self.valence_drift = 0.0
        self.arousal_drift = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("psyche.affect.valence", self.valence)
        port.write("psyche.affect.arousal", self.arousal)

    def step(self, dt: float, port: BusPort) -> None:
        threat = port.read("psyche.appraisal.threat")
        hunger = port.read("psyche.drive.hunger")
        pain = port.read("intero.pain")
        self.valence_drift = ou_step(self.valence_drift, dt, self.fluctuation_tau, self.valence_sigma, self._rng)
        self.arousal_drift = ou_step(self.arousal_drift, dt, self.fluctuation_tau, self.arousal_sigma, self._rng)
        arousal_target = clamp(
            self.w_cardiac_arousal * port.read("intero.cardiac_arousal")
            + self.w_threat_arousal * threat
            + self.w_pain_arousal * pain
            + self.w_novelty_arousal * port.read("psyche.habituation.novelty")
            + self.arousal_drift
        )
        # How unmet demands combine into negative valence: a linear sum lets
        # several mild needs out-vote a single strong one (PSYCHE.md §5), a
        # saturating union (1 - prod(1 - pull)) does not; need_saturation blends.
        pulls = (
            self.w_threat_valence * threat,
            self.w_hunger_valence * hunger,
            self.w_thirst_valence * port.read("psyche.drive.thirst"),
            self.w_thermal_valence * port.read("psyche.drive.thermal_discomfort"),
            self.w_pain_valence * pain,
        )
        linear = sum(pulls)
        union = 1.0
        for pull in pulls:
            union *= 1.0 - clamp(pull, 0.0, 1.0)
        negative_pull = (1.0 - self.need_saturation) * linear + self.need_saturation * (1.0 - union)
        positive_pull = self.w_dopamine_valence * port.read("neuro.dopamine") + self.w_serotonin_valence * (
            port.read("neuro.serotonin") - 0.5
        )
        valence_target = clamp(self.baseline_valence + positive_pull - negative_pull + self.valence_drift, -1.0, 1.0)
        self.arousal = relax(self.arousal, arousal_target, dt, self.tau)
        self.valence = relax(self.valence, valence_target, dt, self.tau)
        port.write("psyche.affect.valence", self.valence)
        port.write("psyche.affect.arousal", self.arousal)
