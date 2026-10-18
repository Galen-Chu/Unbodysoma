"""Action selection: turning internal state into motor commands."""

from __future__ import annotations

from ..core import BusPort, Module, relax


class ActionSelection(Module):
    """A single hard-wired policy: flee while appraised threat is high.

    Hysteresis (start above ``flee_on``, stop below ``flee_off``) prevents
    chattering around the threshold.
    """

    name = "psyche.action"
    rate_hz = 5.0
    reads = ("psyche.appraisal.threat",)
    writes = ("motor.exertion",)
    state_fields = ("fleeing", "exertion")

    def __init__(
        self,
        flee_on: float = 0.5,
        flee_off: float = 0.3,
        flee_exertion: float = 0.8,
        tau: float = 1.0,
    ) -> None:
        self.flee_on = flee_on
        self.flee_off = flee_off
        self.flee_exertion = flee_exertion
        self.tau = tau
        self.fleeing = False
        self.exertion = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("motor.exertion", self.exertion)

    def step(self, dt: float, port: BusPort) -> None:
        threat = port.read("psyche.appraisal.threat")
        if self.fleeing and threat < self.flee_off:
            self.fleeing = False
        elif not self.fleeing and threat > self.flee_on:
            self.fleeing = True
        target = self.flee_exertion if self.fleeing else 0.0
        self.exertion = relax(self.exertion, target, dt, self.tau)
        port.write("motor.exertion", self.exertion)
