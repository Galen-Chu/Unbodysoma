"""Attention: salient domains compete for a broadcast gain (M3 completed).

The minimal global-workspace module (Baars, 1988; PSYCHE §2): six domains —
threat, pain, hunger, thirst, thermal discomfort, sleepiness — compete on
salience; the shares are a bounded softmax, and the current winner keeps a
persistence bias, so focus holds until a challenger clearly outweighs it
(hysteresis, not twitching). Two consumers read the result: appraisal
amplifies attended threat (a threat you are attending to reads larger), and
action selection sharpens with focus — a broadcast domain makes choices less
noisy. Acceptance: tests/test_attention.py; equations: docs/PSYCHE.md §4.12.
"""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

DOMAINS = ("threat", "pain", "hunger", "thirst", "thermal", "sleepiness")


class Attention(Module):
    """Winner-takes-most competition among salient domains."""

    name = "psyche.attention"
    rate_hz = 10.0
    reads = (
        "psyche.appraisal.threat",
        "intero.pain",
        "psyche.drive.hunger",
        "psyche.drive.thirst",
        "psyche.drive.thermal_discomfort",
        "psyche.drive.sleepiness",
    )
    signal_specs = (
        *tuple(SignalSpec(f"psyche.attention.share_{d}", "share", 0.0, 1.0, f"Attention held by {d}") for d in DOMAINS),
        SignalSpec("psyche.attention.focus_share", "share", 0.0, 1.0, "Attention held by the current focus"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "temperature",
            0.1,
            "",
            0.01,
            1.0,
            "Competition softness: small = winner-takes-most, large = evenly divided",
        ),
        ParamSpec(
            "persistence",
            0.5,
            "",
            0.0,
            5.0,
            "Salience bonus for the current focus, holding it against brief challengers",
        ),
        ParamSpec(
            "tau",
            1.0,
            "s",
            0.05,
            60.0,
            "Time constant of share changes",
        ),
    )
    state_fields = ("focus", "shares")

    def __init__(self, temperature: float = 0.1, persistence: float = 0.5, tau: float = 1.0) -> None:
        self.temperature = temperature
        self.persistence = persistence
        self.tau = tau
        self.focus = 0
        self.shares = {d: 1.0 / len(DOMAINS) for d in DOMAINS}

    def _salience(self, port: BusPort) -> dict[str, float]:
        return {
            "threat": port.read("psyche.appraisal.threat"),
            "pain": port.read("intero.pain"),
            "hunger": port.read("psyche.drive.hunger"),
            "thirst": port.read("psyche.drive.thirst"),
            "thermal": port.read("psyche.drive.thermal_discomfort"),
            "sleepiness": port.read("psyche.drive.sleepiness"),
        }

    def _targets(self, salience: dict[str, float]) -> dict[str, float]:
        focus_domain = DOMAINS[self.focus]
        # The winner's bonus scales with its own salience, so an empty field
        # releases the broadcast instead of holding a ghost focus forever.
        bonus = self.persistence * salience[focus_domain]
        weights = {d: salience[d] + (bonus if d == focus_domain else 0.0) for d in DOMAINS}
        peak = max(weights.values())
        exponents = {d: math.exp((w - peak) / self.temperature) for d, w in weights.items()}
        total = sum(exponents.values())
        return {d: exponents[d] / total for d in DOMAINS}

    def step(self, dt: float, port: BusPort) -> None:
        salience = self._salience(port)
        targets = self._targets(salience)
        for d in DOMAINS:
            self.shares[d] += (targets[d] - self.shares[d]) * dt / self.tau
        strongest = max(range(len(DOMAINS)), key=lambda i: salience[DOMAINS[i]])
        if strongest != self.focus and salience[DOMAINS[strongest]] > salience[DOMAINS[self.focus]] + 0.15:
            self.focus = strongest
        for d in DOMAINS:
            port.write(f"psyche.attention.share_{d}", clamp(self.shares[d]))
        port.write("psyche.attention.focus_share", clamp(self.shares[DOMAINS[self.focus]]))
