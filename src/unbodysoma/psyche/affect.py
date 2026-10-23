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
        self.valence_drift = ou_step(self.valence_drift, dt, self.fluctuation_tau, self.valence_sigma, self._rng)
        self.arousal_drift = ou_step(self.arousal_drift, dt, self.fluctuation_tau, self.arousal_sigma, self._rng)
        arousal_target = clamp(
            self.w_cardiac_arousal * port.read("intero.cardiac_arousal")
            + self.w_threat_arousal * threat
            + self.arousal_drift
        )
        valence_target = clamp(
            self.baseline_valence
            - self.w_threat_valence * threat
            - self.w_hunger_valence * hunger
            - self.w_thirst_valence * port.read("psyche.drive.thirst")
            - self.w_thermal_valence * port.read("psyche.drive.thermal_discomfort")
            + self.valence_drift,
            -1.0,
            1.0,
        )
        self.arousal = relax(self.arousal, arousal_target, dt, self.tau)
        self.valence = relax(self.valence, valence_target, dt, self.tau)
        port.write("psyche.affect.valence", self.valence)
        port.write("psyche.affect.arousal", self.arousal)
