"""Observe: recording, health monitoring and (later) visualization of simulation runs.

Everything here is read-only with respect to the simulation: attaching any
observer must never change a run's results. See docs/OBSERVABILITY.md.
"""

from .health import Alert, FiniteRule, HealthMonitor, RangeRule, Rule, SustainedRule, default_rules, spec_rules
from .recorder import Recorder
from .run import Run, RunWriter, load_run

__all__ = [
    "Alert",
    "FiniteRule",
    "HealthMonitor",
    "RangeRule",
    "Recorder",
    "Rule",
    "Run",
    "RunWriter",
    "SustainedRule",
    "default_rules",
    "load_run",
    "spec_rules",
]
