"""Action selection: turning internal state into motor commands."""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, relax

IDLE, FLEE, EAT = "idle", "flee", "eat"


class ActionSelection(Module):
    """Hard-wired, prioritized policy: flee from threat, otherwise eat when hungry and food is near.

    Each behaviour uses hysteresis (start above an ``*_on`` threshold, stop
    below an ``*_off`` threshold) to prevent chattering. Fleeing pre-empts
    eating; an interrupted meal resumes once the threat has passed if hunger
    is still above ``eat_on``. Phase 1 replaces this with probabilistic
    competition between actions (see docs/VARIABILITY.md).
    """

    name = "psyche.action"
    rate_hz = 5.0
    reads = ("psyche.appraisal.threat", "psyche.drive.hunger", "extero.food")
    signal_specs = (
        SignalSpec("motor.exertion", "normalized", 0.0, 1.0, "Physical effort being exerted"),
        SignalSpec("motor.eating", "normalized", 0.0, 1.0, "Eating behaviour (1 = eating)"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("flee_on", 0.5, "normalized", 0.0, 1.0, "Appraised threat that starts flight"),
        ParamSpec("flee_off", 0.3, "normalized", 0.0, 1.0, "Appraised threat below which flight stops"),
        ParamSpec("flee_exertion", 0.8, "normalized", 0.0, 1.0, "Exertion while fleeing"),
        ParamSpec("eat_on", 0.4, "normalized", 0.0, 1.0, "Hunger that starts eating when food is near"),
        ParamSpec("eat_off", 0.1, "normalized", 0.0, 1.0, "Hunger below which eating stops (satiety)"),
        ParamSpec("food_seen", 0.5, "normalized", 0.0, 1.0, "Sensed food level that counts as food within reach"),
        ParamSpec("tau", 1.0, "s", 0.01, 60.0, "Time constant of exertion changes"),
    )
    state_fields = ("mode", "exertion")

    def __init__(
        self,
        flee_on: float = 0.5,
        flee_off: float = 0.3,
        flee_exertion: float = 0.8,
        eat_on: float = 0.4,
        eat_off: float = 0.1,
        food_seen: float = 0.5,
        tau: float = 1.0,
    ) -> None:
        self.flee_on = flee_on
        self.flee_off = flee_off
        self.flee_exertion = flee_exertion
        self.eat_on = eat_on
        self.eat_off = eat_off
        self.food_seen = food_seen
        self.tau = tau
        self.mode = IDLE
        self.exertion = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("motor.exertion", self.exertion)
        port.write("motor.eating", 0.0)

    def _next_mode(self, threat: float, hunger: float, food_near: bool) -> str:
        if self.mode == FLEE:
            if threat >= self.flee_off:
                return FLEE
        elif threat > self.flee_on:
            return FLEE
        if self.mode == EAT and food_near and hunger >= self.eat_off:
            return EAT
        if food_near and hunger > self.eat_on:
            return EAT
        return IDLE

    def step(self, dt: float, port: BusPort) -> None:
        self.mode = self._next_mode(
            threat=port.read("psyche.appraisal.threat"),
            hunger=port.read("psyche.drive.hunger"),
            food_near=port.read("extero.food") > self.food_seen,
        )
        target = self.flee_exertion if self.mode == FLEE else 0.0
        self.exertion = relax(self.exertion, target, dt, self.tau)
        port.write("motor.exertion", self.exertion)
        port.write("motor.eating", 1.0 if self.mode == EAT else 0.0)
