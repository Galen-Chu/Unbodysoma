"""Health monitoring: automatic checks that a run stays physiologically and numerically sane."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from ..core import BusReader, Engine, SignalSpec

SEVERITIES = ("info", "warning", "critical")
_EPS = 1e-9


@dataclass(frozen=True)
class Alert:
    t: float
    rule: str
    subject: str
    severity: str
    message: str
    raised: bool  # False when the condition has cleared


class Rule(ABC):
    name: str
    severity: str

    @abstractmethod
    def violations(self, t: float, bus: BusReader) -> dict[str, str]:
        """Currently violated subjects (usually signal keys) mapped to a human-readable message."""


class FiniteRule(Rule):
    """Every signal must be a finite number."""

    def __init__(self, severity: str = "critical", name: str = "finite") -> None:
        self.name = name
        self.severity = severity

    def violations(self, t: float, bus: BusReader) -> dict[str, str]:
        return {k: f"{k} is {v}" for k, v in bus.snapshot().items() if not math.isfinite(v)}


class RangeRule(Rule):
    """A signal must stay within ``[lo, hi]``."""

    def __init__(self, key: str, lo: float, hi: float, severity: str = "warning", name: str | None = None) -> None:
        self.key = key
        self.lo = lo
        self.hi = hi
        self.severity = severity
        self.name = name or f"range:{key}"

    def violations(self, t: float, bus: BusReader) -> dict[str, str]:
        if self.key not in bus:
            return {}
        value = bus.read(self.key)
        if self.lo <= value <= self.hi:
            return {}
        return {self.key: f"{self.key} = {value:.4g} outside [{self.lo:g}, {self.hi:g}]"}


class SustainedRule(Rule):
    """A signal must not stay beyond a threshold for longer than ``duration`` seconds."""

    def __init__(
        self,
        key: str,
        duration: float,
        below: float | None = None,
        above: float | None = None,
        severity: str = "warning",
        name: str | None = None,
    ) -> None:
        if (below is None) == (above is None):
            raise ValueError("give exactly one of below= or above=")
        self.key = key
        self.duration = duration
        self.below = below
        self.above = above
        self.severity = severity
        self.name = name or f"sustained:{key}"
        self._since: float | None = None

    def violations(self, t: float, bus: BusReader) -> dict[str, str]:
        value = bus.read(self.key)
        if self.below is not None:
            beyond = value < self.below
        else:
            assert self.above is not None  # guaranteed by __init__
            beyond = value > self.above
        if not beyond:
            self._since = None
            return {}
        if self._since is None:
            self._since = t
        held = t - self._since
        if held + _EPS < self.duration:
            return {}
        side = f"< {self.below:g}" if self.below is not None else f"> {self.above:g}"
        return {self.key: f"{self.key} {side} for {held:.0f} s"}


def default_rules() -> list[Rule]:
    """Sanity limits for the Phase 0 organism. Thresholds are coarse, not clinical."""
    return [
        FiniteRule(),
        RangeRule("soma.cardio.heart_rate", 30.0, 220.0, "critical", name="heart_rate_survivable"),
        RangeRule("soma.cardio.heart_rate", 40.0, 180.0, "warning", name="heart_rate_abnormal"),
        RangeRule("soma.metabolism.glucose", 50.0, 200.0, "warning", name="glucose_abnormal"),
        RangeRule("soma.metabolism.energy_reserve", 0.05, 1.0, "warning", name="starvation"),
        # docs/ETHICS.md §3: prolonged strongly negative states must be visible.
        SustainedRule("psyche.affect.valence", 120.0, below=-0.5, name="prolonged_negative_valence"),
    ]


def spec_rules(specs: Iterable[SignalSpec], severity: str = "critical") -> list[Rule]:
    """One range rule per bounded signal spec. A spec violation means a model bug, hence critical."""
    return [
        RangeRule(s.key, s.lo, s.hi, severity, name=f"spec:{s.key}")
        for s in specs
        if math.isfinite(s.lo) or math.isfinite(s.hi)
    ]


class HealthMonitor:
    """Engine observer that evaluates rules, logs alert transitions and can halt the run.

    Alerts are emitted only when a condition is raised or cleared, not on every
    sample. With ``halt_on="critical"`` a critical alert stops ``Engine.run``.
    With ``check_specs`` (default), every signal is also checked against the
    valid range declared in its ``SignalSpec``.
    """

    def __init__(
        self,
        rules: Iterable[Rule] | None = None,
        every: float = 0.1,
        halt_on: str | None = None,
        check_specs: bool = True,
    ) -> None:
        if halt_on is not None and halt_on not in SEVERITIES:
            raise ValueError(f"halt_on must be one of {SEVERITIES} or None")
        self.rules = list(default_rules() if rules is None else rules)
        self.every = every
        self.halt_on = halt_on
        self.check_specs = check_specs
        self.alerts: list[Alert] = []
        self.active: dict[tuple[str, str], Alert] = {}
        self._engine: Engine | None = None
        self._next = 0.0

    def attach(self, engine: Engine) -> HealthMonitor:
        self._engine = engine
        if self.check_specs:
            self.rules.extend(spec_rules(engine.signal_specs().values()))
        engine.observe(self)
        return self

    @property
    def worst(self) -> str | None:
        """Highest severity raised so far."""
        raised = {a.severity for a in self.alerts if a.raised}
        return max(raised, key=SEVERITIES.index) if raised else None

    def __call__(self, t: float, bus: BusReader) -> None:
        if t + _EPS < self._next:
            return
        self._next += self.every
        for rule in self.rules:
            current = rule.violations(t, bus)
            for subject, message in current.items():
                if (rule.name, subject) not in self.active:
                    self._emit(Alert(t, rule.name, subject, rule.severity, message, raised=True))
            for (name, subject), alert in list(self.active.items()):
                if name == rule.name and subject not in current:
                    self._emit(Alert(t, name, subject, alert.severity, f"{subject} back to normal", raised=False))

    def _emit(self, alert: Alert) -> None:
        self.alerts.append(alert)
        key = (alert.rule, alert.subject)
        if alert.raised:
            self.active[key] = alert
        else:
            del self.active[key]
        if self._engine is None:
            return
        kind = "health.alert" if alert.raised else "health.cleared"
        self._engine.record_event(
            kind, t=alert.t, rule=alert.rule, subject=alert.subject, severity=alert.severity, message=alert.message
        )
        if alert.raised and self.halt_on and SEVERITIES.index(alert.severity) >= SEVERITIES.index(self.halt_on):
            self._engine.request_stop(f"health: {alert.message}")
