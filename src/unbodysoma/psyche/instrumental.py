"""Instrumental learning: actions followed by outcomes change their value.

Thorndike's law of effect in its minimal, eligibility-trace form: while an
action is being performed its eligibility rises (and decays over tens of
seconds afterwards); whatever outcome arrives — relief (positive) or felt
pain (negative) — shifts the eligible actions' learned value. Action
selection adds the values to its utilities, so rewarded actions become more
likely and punished ones less, without any new hardwired rule.

Punishment is gated on the *rising edge* of pain — the moment something
newly hurt — not on the sustained ache of an existing injury: an organism
limping home for a day should not learn to hate walking, sleeping and
eating. Reward needs no such gate (relief is inherently an event).

Honest limitation (docs/PSYCHE.md §4.8): credit is action-level only — pain
that arrives while fleeing punishes fleeing a little, because the trace
cannot know the flee was a *response to* the pain. Place-level credit is the
place-memory module's job (§4.10); the two are complementary.
Acceptance: tests/test_instrumental.py.
"""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp
from .action import ACTIONS


class Instrumental(Module):
    """Law-of-effect values per action, learned through eligibility traces."""

    name = "psyche.instrumental"
    rate_hz = 10.0
    reads = tuple(f"psyche.action.selected_{a}" for a in ACTIONS) + ("neuro.relief", "intero.pain")
    signal_specs = tuple(
        SignalSpec(f"psyche.instrumental.value_{a}", "utility", -1.0, 1.0, f"Learned value of {a}") for a in ACTIONS
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "learn_rate",
            0.01,
            "1/s",
            0.0,
            1.0,
            "Value change per second of unit eligibility and unit outcome",
            source="calibrated: a meal lifts the value of eating, a day without reinforcement forgets it",
        ),
        ParamSpec(
            "tau_eligibility",
            20.0,
            "s",
            1.0,
            600.0,
            "Time constant of the eligibility trace after the action ends",
            source="seconds-scale credit assignment (the trace bridges action to delayed outcome)",
        ),
        ParamSpec(
            "tau_forgetting",
            1800.0,
            "s",
            60.0,
            86400.0,
            "Time constant of value decay without reinforcement (extinction)",
        ),
        ParamSpec(
            "w_pain",
            1.0,
            "",
            0.0,
            5.0,
            "Punishing strength of rising pain, relative to the rewarding strength of relief",
        ),
        ParamSpec(
            "tau_pain_trace",
            5.0,
            "s",
            0.5,
            120.0,
            "Trailing average of pain; only pain above it punishes (the rising edge)",
            source="calibrated: a fresh injury punishes for seconds, a lingering ache not at all",
        ),
    )
    state_fields = ("eligibility", "value", "pain_trace")

    def __init__(
        self,
        learn_rate: float = 0.01,
        tau_eligibility: float = 20.0,
        tau_forgetting: float = 1800.0,
        w_pain: float = 1.0,
        tau_pain_trace: float = 5.0,
    ) -> None:
        self.learn_rate = learn_rate
        self.tau_eligibility = tau_eligibility
        self.tau_forgetting = tau_forgetting
        self.w_pain = w_pain
        self.tau_pain_trace = tau_pain_trace
        self.eligibility = {a: 0.0 for a in ACTIONS}
        self.value = {a: 0.0 for a in ACTIONS}
        self.pain_trace = 0.0

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    def step(self, dt: float, port: BusPort) -> None:
        pain = port.read("intero.pain")
        rising = max(0.0, pain - self.pain_trace)
        self.pain_trace += (pain - self.pain_trace) * dt / self.tau_pain_trace
        outcome = port.read("neuro.relief") - self.w_pain * rising
        for a in ACTIONS:
            selected = port.read(f"psyche.action.selected_{a}")
            self.eligibility[a] = max(selected, self.eligibility[a] - self.eligibility[a] * dt / self.tau_eligibility)
            self.value[a] = clamp(
                self.value[a]
                + dt * self.learn_rate * self.eligibility[a] * outcome
                - dt * self.value[a] / self.tau_forgetting,
                -1.0,
                1.0,
            )
        self._publish(port)

    def _publish(self, port: BusPort) -> None:
        for a in ACTIONS:
            port.write(f"psyche.instrumental.value_{a}", self.value[a])
