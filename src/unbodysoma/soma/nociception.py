"""Nociception: tissue damage, first/second pain and sensitization (L1-lite).

Damage arriving from the world (a hazard, later a conditioning US) is turned
into a slowly-healing injury state and two pain components with the classic
temporal separation of the dual pain response: a fast "sharp" phase that
tracks the stimulus (A-delta fibres) and a delayed "burning" phase that tracks
tissue state (C fibres) and outlasts the stimulus. Repeated noxious input
sensitizes the pathway (wind-up / primary hyperalgesia), multiplying felt
intensity for a while.

Anchors: Julius & Basbaum (2001) for the fibre classes and hyperalgesia,
Mendell (1966) for C-fibre wind-up under repeated stimulation. Acceptance
bounds in tests/test_nociception.py; equations in docs/SOMA.md §2.9.
"""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax


class Nociception(Module):
    """Damage → injury + sharp/burning pain, with use-dependent sensitization."""

    name = "soma.nociception"
    rate_hz = 10.0
    reads = ("world.damage",)
    signal_specs = (
        SignalSpec("soma.nociception.injury", "fraction", 0.0, 1.0, "Tissue injury (1 = maximally injured)"),
        SignalSpec("soma.nociception.sharp", "normalized", 0.0, 1.0, "First pain: fast, tracks the stimulus"),
        SignalSpec("soma.nociception.burning", "normalized", 0.0, 1.0, "Second pain: slow, tracks tissue state"),
        SignalSpec("soma.nociception.pain", "normalized", 0.0, 1.0, "Felt pain intensity (sensitized)"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "injury_gain",
            0.03,
            "1/s",
            0.0,
            1.0,
            "Injury accumulated per second of unit damage",
            source="calibrated: a 2 s graze reads as a mild ache, a minute of contact as a serious wound",
        ),
        ParamSpec(
            "tau_heal",
            86400.0,
            "s",
            3600.0,
            604800.0,
            "Time constant of tissue healing",
            source="order of magnitude: tissue repair operates over hours to days",
        ),
        ParamSpec(
            "tau_sharp",
            1.5,
            "s",
            0.05,
            10.0,
            "Decay of first pain",
            source="fast A-delta signalling (Julius & Basbaum 2001)",
        ),
        ParamSpec(
            "tau_burning",
            25.0,
            "s",
            1.0,
            300.0,
            "Rise and decay of second pain",
            source="slow C-fibre signalling; second pain outlasts the stimulus (Julius & Basbaum 2001)",
        ),
        ParamSpec(
            "burning_gain",
            2.5,
            "",
            0.0,
            10.0,
            "Second-pain intensity per unit injury",
            source="calibrated: a half-saturated injury reads as near-maximal burning pain",
        ),
        ParamSpec(
            "sensitization_rate",
            0.1,
            "1/s",
            0.0,
            1.0,
            "Sensitization gained per second of unit damage",
            source="wind-up: repeated C-fibre input grows the response (Mendell 1966)",
        ),
        ParamSpec(
            "tau_sensitization",
            900.0,
            "s",
            10.0,
            86400.0,
            "Decay of sensitization after the damage stops",
            source="primary hyperalgesia fades over minutes",
        ),
        ParamSpec(
            "max_sensitization",
            1.0,
            "x",
            0.0,
            3.0,
            "Upper bound of the pain multiplier (1 + this)",
            source="hyperalgesia roughly doubles reported intensity",
        ),
    )
    state_fields = ("injury", "sharp", "burning", "sensitization")

    def __init__(
        self,
        injury_gain: float = 0.03,
        tau_heal: float = 86400.0,
        tau_sharp: float = 1.5,
        tau_burning: float = 25.0,
        burning_gain: float = 2.5,
        sensitization_rate: float = 0.1,
        tau_sensitization: float = 900.0,
        max_sensitization: float = 1.0,
    ) -> None:
        self.injury_gain = injury_gain
        self.tau_heal = tau_heal
        self.tau_sharp = tau_sharp
        self.tau_burning = tau_burning
        self.burning_gain = burning_gain
        self.sensitization_rate = sensitization_rate
        self.tau_sensitization = tau_sensitization
        self.max_sensitization = max_sensitization
        self.injury = 0.0
        self.sharp = 0.0
        self.burning = 0.0
        self.sensitization = 0.0

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    def step(self, dt: float, port: BusPort) -> None:
        damage = port.read("world.damage")
        # Tissue state integrates damage and heals on a much slower clock.
        self.injury = clamp(self.injury + dt * (self.injury_gain * damage - self.injury / self.tau_heal))
        # First pain tracks the stimulus; second pain tracks the injury.
        self.sharp = relax(self.sharp, damage, dt, self.tau_sharp)
        self.burning = relax(self.burning, clamp(self.burning_gain * self.injury), dt, self.tau_burning)
        # Use-dependent sensitization: accumulates under repeated damage, fades slowly.
        self.sensitization = clamp(
            self.sensitization + dt * (self.sensitization_rate * damage - self.sensitization / self.tau_sensitization)
        )
        self._publish(port)

    def _publish(self, port: BusPort) -> None:
        pain = clamp((self.sharp + self.burning) * (1.0 + self.max_sensitization * self.sensitization))
        port.write("soma.nociception.injury", self.injury)
        port.write("soma.nociception.sharp", self.sharp)
        port.write("soma.nociception.burning", self.burning)
        port.write("soma.nociception.pain", pain)
