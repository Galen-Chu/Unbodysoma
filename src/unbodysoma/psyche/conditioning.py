"""Classical conditioning: Rescorla–Wagner in continuous time, spectrally timed.

Two cues (``world.stimulus`` = A, ``world.stimulus_b`` = B) acquire
associative strength from two unconditioned stimuli:

- **defense**: US = ``world.damage``, scalar presence-based Rescorla–Wagner.
  The summed prediction of the cues present enters appraisal as learned
  threat, so a conditioned cue alone produces a defensive response, and an
  established cue blocks a new one added in compound (Kamin) — because
  prediction error, not US occurrence, drives learning. The US is coterminous
  with the cue in every defense pairing, so presence states carry enough
  timing.
- **reward**: US = ``neuro.relief``, expanded over a bank of decaying traces
  (spectral timing: each cue onset triggers a cascade of exponentials with
  log-spaced time constants, Grossberg & Schmajuk 1989; Ludvig, Sutton &
  Kehoe 2008). A temporal-difference error over the cascade carries credit
  across the delay between cue and relief: after learning, value jumps at
  cue *onset*, and the published dopamine error decomposes into the RW error
  of arriving relief against the held expectation (predicted relief does not
  surprise; a predictor without its reward dips below tonic until its traces
  die) plus the cue-onset commitment burst — the anticipatory response that
  presence-state TD could not produce (measured 2026-11-27: v[none] > v[a]
  under delayed relief). Trace-conditioning honesty: at our physiological
  delay (~10 min gut absorption) the transfer to the cue is partial — the
  gamma discount caps it — matching how hard long-interval trace
  conditioning is in the behavioral literature.

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

# The spectral bank: trace time constants, log-spaced ~10 s .. 1500 s. Cue
# onset resets every trace to the cue's intensity; each then decays alone,
# so the bank encodes "time since onset" (Grossberg & Schmajuk 1989).
_SPECTRUM = tuple(10.0 * (1500.0 / 10.0) ** (i / 11) for i in range(12))


class Conditioning(Module):
    """Associative strength per cue, learned from prediction error."""

    name = "psyche.conditioning"
    rate_hz = 10.0
    reads = ("world.stimulus", "world.stimulus_b", "world.damage", "neuro.relief")
    signal_specs = (
        SignalSpec(
            "psyche.conditioning.threat_expectation", "normalized", 0.0, 1.0, "Learned threat predicted by present cues"
        ),
        SignalSpec(
            "psyche.conditioning.reward_prediction",
            "normalized",
            0.0,
            1.0,
            "Relief value predicted by the cue-time cascade",
        ),
        SignalSpec(
            "psyche.conditioning.reward_error",
            "normalized",
            -1.0,
            1.0,
            "Dopamine RPE: arriving relief minus held expectation, plus the cue-onset burst",
        ),
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
            "Defense association change per second of unit cue and unit prediction error (RW's alpha*beta)",
            source="calibrated: ~10 two-second pairings reach two-thirds of asymptote",
        ),
        ParamSpec(
            "defense_asymptote",
            1.0,
            "",
            0.0,
            2.0,
            "Associative asymptote supported by unit damage (RW's lambda)",
        ),
        ParamSpec(
            "reward_asymptote",
            1.0,
            "",
            0.0,
            5.0,
            "Reward-value asymptote per unit relief rate (scales the per-step reward mass)",
            source="the predicted value must match the relief scale for the dopamine error to be signed correctly",
        ),
        ParamSpec(
            "learn_rate_reward",
            1.0,
            "1/s",
            0.0,
            10.0,
            "Spectral-trace weight change per second of unit trace and unit TD error (LMS-normalized by trace energy)",
        ),
        ParamSpec(
            "tau_gamma",
            900.0,
            "s",
            60.0,
            7200.0,
            "Discount time constant of the spectral TD error (longer = less discounting, more transfer)",
        ),
        ParamSpec(
            "tau_reward_mass",
            240.0,
            "s",
            30.0,
            3600.0,
            "Relief integration time converting relief rate to value mass (unit relief this long = unit value)",
        ),
        ParamSpec(
            "tau_onset_burst",
            8.0,
            "s",
            0.5,
            30.0,
            "Decay of the cue-onset dopamine burst (phasic response width)",
        ),
        ParamSpec(
            "tau_prediction_hold",
            10.0,
            "s",
            0.5,
            60.0,
            "Release time of a fresh prediction into the dopamine baseline (burst first, dip after)",
        ),
        ParamSpec(
            "w_onset_burst",
            1.0,
            "",
            0.0,
            5.0,
            "Dopamine burst per unit of value committed at a cue onset (the cue-onset transfer response)",
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
    state_fields = ("defense", "reward_basis", "reward_w", "cue_prev", "deep", "absent", "burst", "v_hold")

    def __init__(
        self,
        learn_rate: float = 0.05,
        defense_asymptote: float = 1.0,
        reward_asymptote: float = 1.0,
        learn_rate_reward: float = 1.0,
        tau_gamma: float = 900.0,
        tau_reward_mass: float = 240.0,
        w_onset_burst: float = 1.0,
        tau_onset_burst: float = 8.0,
        tau_prediction_hold: float = 10.0,
        tau_deep_rise: float = 900.0,
        tau_deep_decay: float = 86400.0,
        recovery_share: float = 0.7,
        rest_refractory: float = 120.0,
        tau_recovery: float = 600.0,
    ) -> None:
        self.learn_rate = learn_rate
        self.defense_asymptote = defense_asymptote
        self.reward_asymptote = reward_asymptote
        self.learn_rate_reward = learn_rate_reward
        self.tau_gamma = tau_gamma
        self.tau_reward_mass = tau_reward_mass
        self.w_onset_burst = w_onset_burst
        self.tau_onset_burst = tau_onset_burst
        self.tau_prediction_hold = tau_prediction_hold
        self.burst = 0.0
        self.v_hold = 0.0
        self.tau_deep_rise = tau_deep_rise
        self.tau_deep_decay = tau_deep_decay
        self.recovery_share = recovery_share
        self.rest_refractory = rest_refractory
        self.tau_recovery = tau_recovery
        self.defense = {"a": 0.0, "b": 0.0}
        self.reward_basis = {c: [0.0] * len(_SPECTRUM) for c in _CUES}
        self.reward_w = {c: [0.0] * len(_SPECTRUM) for c in _CUES}
        self.cue_prev = {"a": 0.0, "b": 0.0}
        self.deep = {"a": 0.0, "b": 0.0}
        self.absent = {"a": math.inf, "b": math.inf}

    def setup(self, port: BusPort) -> None:
        self._publish(port, {"a": 0.0, "b": 0.0}, 0.0, 0.0)

    def step(self, dt: float, port: BusPort) -> None:
        cues = {c: port.read(sig) for c, sig in _CUE_SIGNALS.items()}
        damage = port.read("world.damage")
        relief = port.read("neuro.relief")

        # Defense: plain Rescorla–Wagner — prediction error against the total
        # prediction of all present cues, applied to each present cue in
        # proportion to its intensity (the cue's salience, alpha).
        total_defense = sum(self.defense[c] * cues[c] for c in _CUES)
        error_defense = self.defense_asymptote * damage - total_defense
        for c in _CUES:
            self.defense[c] = clamp(self.defense[c] + dt * self.learn_rate * cues[c] * error_defense)

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

        # Reward: spectral timing. Cue onsets reset the trace cascade; value
        # is the weighted cascade; the TD error against the discounted value
        # change carries credit from the delayed relief back to the traces
        # that were active when the cue arrived.
        v_before = self._reward_value()
        onset_jump = 0.0
        for c in _CUES:
            basis = self.reward_basis[c]
            onset = cues[c] > self.cue_prev[c]  # rising edge only: traces encode time since onset
            for k, tau in enumerate(_SPECTRUM):
                decayed = basis[k] * math.exp(-dt / tau)
                basis[k] = max(decayed, cues[c]) if onset else decayed
            self.cue_prev[c] = cues[c]
        v_after = self._reward_value()
        if v_after - v_before > onset_jump:
            onset_jump = v_after - v_before
        # The burst is a phasic state, not a one-tick event: dopamine's own
        # low-pass would filter a single-step jump away entirely.
        self.burst = max(self.burst * math.exp(-dt / self.tau_onset_burst), onset_jump)
        rho = self.reward_asymptote * relief * dt / self.tau_reward_mass
        delta = rho + math.exp(-dt / self.tau_gamma) * v_after - v_before
        energy = sum(b * b for c in _CUES for b in self.reward_basis[c]) + 1e-9
        for c in _CUES:
            weights = self.reward_w[c]
            for k, b in enumerate(self.reward_basis[c]):
                weights[k] += dt * self.learn_rate_reward * b * delta / energy

        # The dopamine RPE, decomposed (each part literature-anchored): the
        # RW error between arriving relief and the held expectation --
        # predicted relief does not surprise, and a predictor without its
        # reward dips below tonic for as long as its traces hold value --
        # plus the cue-onset commitment burst, the value jump when a
        # predictor appears (the Schultz cue-onset transfer response). The
        # expectation enters through a short hold filter, so a fresh
        # prediction bursts first and only then becomes the baseline that
        # absence reads against. Without cues both terms are zero and the
        # error is plain relief.
        self.v_hold += (v_after - self.v_hold) * dt / self.tau_prediction_hold
        error_level = self.reward_asymptote * relief - self.v_hold + self.w_onset_burst * self.burst
        self._publish(port, cues, v_after, error_level)

    def _reward_value(self) -> float:
        return sum(sum(w * b for w, b in zip(self.reward_w[c], self.reward_basis[c], strict=True)) for c in _CUES)

    def _publish(self, port: BusPort, cues: dict[str, float], reward_value: float, reward_error: float) -> None:
        threat = sum(self.defense[c] * cues[c] for c in _CUES)
        port.write("psyche.conditioning.threat_expectation", clamp(threat))
        port.write("psyche.conditioning.reward_prediction", clamp(reward_value))
        port.write("psyche.conditioning.reward_error", clamp(reward_error, -1.0, 1.0))
        port.write("psyche.conditioning.defense_a", self.defense["a"])
        port.write("psyche.conditioning.defense_b", self.defense["b"])
