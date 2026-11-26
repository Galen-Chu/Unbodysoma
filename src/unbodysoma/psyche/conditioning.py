"""Classical conditioning: Rescorla–Wagner associations in continuous time.

Two cues (``world.stimulus`` = A, ``world.stimulus_b`` = B) acquire
associative strength from two unconditioned stimuli:

- **defense**: US = ``world.damage``. The summed prediction of the cues
  present enters appraisal as learned threat, so a conditioned cue alone
  produces a defensive response, and an established cue blocks a new one
  added in compound (Kamin) — because prediction error, not US occurrence,
  drives learning.
- **reward**: US = ``neuro.relief``. The summed prediction feeds the dopamine
  RPE (``relief − prediction``), so predicted relief stops surprising and a
  cue without its reward produces an omission dip (Schultz et al. 1997).

Cue identity is the channel: two cues are enough for acquisition,
extinction, spontaneous recovery and blocking; richer representations wait
for the episodic-memory design. Spontaneous recovery is minimal-honest: a
slow consolidated trace of the association that re-merges into the fast
state during rest, one-sided (rest can recover, exposure alone extinguishes).
Acceptance: tests/test_conditioning.py; equations: docs/PSYCHE.md §4.7.
"""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

_CUES = ("a", "b")
_CUE_SIGNALS = {"a": "world.stimulus", "b": "world.stimulus_b"}


class Conditioning(Module):
    """Associative strength per cue, learned from prediction error."""

    name = "psyche.conditioning"
    rate_hz = 10.0
    reads = ("world.stimulus", "world.stimulus_b", "world.damage", "neuro.relief")
    signal_specs = (
        SignalSpec(
            "psyche.conditioning.threat_expectation", "normalized", 0.0, 1.0, "Learned threat predicted by present cues"
        ),
        SignalSpec("psyche.conditioning.reward_prediction", "normalized", 0.0, 1.0, "Relief predicted by present cues"),
        SignalSpec("psyche.conditioning.defense_a", "normalized", 0.0, 1.0, "Defensive association of cue A"),
        SignalSpec("psyche.conditioning.defense_b", "normalized", 0.0, 1.0, "Defensive association of cue B"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "learn_rate",
            0.05,
            "1/s",
            0.0,
            1.0,
            "Association change per second of unit cue and unit prediction error (RW's αβ)",
            source="calibrated: ~10 two-second pairings reach two-thirds of asymptote",
        ),
        ParamSpec(
            "defense_asymptote",
            1.0,
            "",
            0.0,
            2.0,
            "Associative asymptote supported by unit damage (RW's λ)",
        ),
        ParamSpec(
            "reward_asymptote",
            1.0,
            "",
            0.0,
            5.0,
            "Associative asymptote per unit relief (predictions stay in relief units, matching the RPE)",
            source="the prediction must match the relief scale for the dopamine error to be signed correctly",
        ),
        ParamSpec(
            "tau_deep_rise",
            900.0,
            "s",
            60.0,
            86400.0,
            "Time constant of the consolidated trace while the association is strong",
        ),
        ParamSpec(
            "tau_deep_decay",
            86400.0,
            "s",
            600.0,
            604800.0,
            "Time constant of the consolidated trace while the association is gone",
        ),
        ParamSpec(
            "recovery_share",
            0.7,
            "",
            0.0,
            1.0,
            "Share of the consolidated trace that rest can bring back",
            source="spontaneous recovery is partial (Rankin et al. 2009)",
        ),
        ParamSpec(
            "rest_refractory",
            120.0,
            "s",
            5.0,
            3600.0,
            "Cue absence required before spontaneous recovery starts (recovery follows rest, not trial gaps)",
        ),
        ParamSpec(
            "tau_recovery",
            600.0,
            "s",
            30.0,
            86400.0,
            "Time constant of spontaneous recovery during rest",
        ),
    )
    state_fields = ("defense", "reward", "deep", "absent")

    def __init__(
        self,
        learn_rate: float = 0.05,
        defense_asymptote: float = 1.0,
        reward_asymptote: float = 1.0,
        tau_deep_rise: float = 900.0,
        tau_deep_decay: float = 86400.0,
        recovery_share: float = 0.7,
        rest_refractory: float = 120.0,
        tau_recovery: float = 600.0,
    ) -> None:
        self.learn_rate = learn_rate
        self.defense_asymptote = defense_asymptote
        self.reward_asymptote = reward_asymptote
        self.tau_deep_rise = tau_deep_rise
        self.tau_deep_decay = tau_deep_decay
        self.recovery_share = recovery_share
        self.rest_refractory = rest_refractory
        self.tau_recovery = tau_recovery
        self.defense = {"a": 0.0, "b": 0.0}
        self.reward = {"a": 0.0, "b": 0.0}
        self.deep = {"a": 0.0, "b": 0.0}
        self.absent = {"a": math.inf, "b": math.inf}

    def setup(self, port: BusPort) -> None:
        self._publish(port, {"a": 0.0, "b": 0.0})

    def step(self, dt: float, port: BusPort) -> None:
        cues = {c: port.read(sig) for c, sig in _CUE_SIGNALS.items()}
        damage = port.read("world.damage")
        relief = port.read("neuro.relief")

        # Rescorla–Wagner in continuous time: prediction error against the
        # total prediction of all present cues, applied to each present cue
        # in proportion to its intensity (the cue's salience, α).
        total_defense = sum(self.defense[c] * cues[c] for c in _CUES)
        total_reward = sum(self.reward[c] * cues[c] for c in _CUES)
        error_defense = self.defense_asymptote * damage - total_defense
        error_reward = self.reward_asymptote * relief - total_reward
        for c in _CUES:
            self.defense[c] = clamp(self.defense[c] + dt * self.learn_rate * cues[c] * error_defense)
            self.reward[c] = clamp(self.reward[c] + dt * self.learn_rate * cues[c] * error_reward)

            # Consolidated trace (defense only): rises while the association
            # is strong, decays slowly once it is gone...
            if self.defense[c] > self.deep[c]:
                self.deep[c] += (self.defense[c] - self.deep[c]) * dt / self.tau_deep_rise
            else:
                self.deep[c] += (self.defense[c] - self.deep[c]) * dt / self.tau_deep_decay

            # ...and rest can bring a share of it back — one-sided (never
            # fights acquisition) and gated on sustained absence, so the gaps
            # between extinction trials do not undo the extinction.
            self.absent[c] = 0.0 if cues[c] > 0.1 else self.absent[c] + dt
            if self.absent[c] > self.rest_refractory:
                target = self.recovery_share * self.deep[c]
                if target > self.defense[c]:
                    self.defense[c] += (target - self.defense[c]) * dt / self.tau_recovery

        self._publish(port, cues)

    def _publish(self, port: BusPort, cues: dict[str, float]) -> None:
        threat = sum(self.defense[c] * cues[c] for c in _CUES)
        reward = sum(self.reward[c] * cues[c] for c in _CUES)
        port.write("psyche.conditioning.threat_expectation", clamp(threat))
        port.write("psyche.conditioning.reward_prediction", clamp(reward))
        port.write("psyche.conditioning.defense_a", self.defense["a"])
        port.write("psyche.conditioning.defense_b", self.defense["b"])
