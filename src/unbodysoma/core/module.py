"""The contract every simulated subsystem (body or mind) implements."""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import Any

from .bus import BusPort
from .specs import ParamSpec, SignalSpec


class Module(ABC):
    """A subsystem that advances its own state at a fixed rate.

    Subclasses declare which signals they ``reads`` and ``writes``. The engine
    uses these declarations to enforce a single writer per signal and to
    detect reads that nothing produces.

    Every attribute that changes during ``step`` must be listed in
    ``state_fields`` (or handled by overriding ``get_state`` / ``set_state``),
    so that the engine can snapshot and restore the whole simulation.
    See docs/adr/0004-explicit-module-state.md.

    Tunable constants are declared in ``params`` (one ``ParamSpec`` per
    ``__init__`` argument, stored under the same attribute name) and outputs
    are described in ``signal_specs``. See docs/adr/0006-declarative-parameter-and-signal-specs.md.
    """

    name: str = "module"
    rate_hz: float = 10.0
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    state_fields: tuple[str, ...] = ()
    params: tuple[ParamSpec, ...] = ()
    signal_specs: tuple[SignalSpec, ...] = ()

    def setup(self, port: BusPort) -> None:  # noqa: B027 - optional hook
        """Publish initial values. Called once before the first tick."""

    @abstractmethod
    def step(self, dt: float, port: BusPort) -> None:
        """Advance internal state by ``dt`` seconds and publish outputs."""

    def get_params(self) -> dict[str, Any]:
        """Current parameter values, as recorded in run records."""
        return {spec.name: getattr(self, spec.name) for spec in self.params}

    def get_state(self) -> dict[str, Any]:
        return {field: copy.deepcopy(getattr(self, field)) for field in self.state_fields}

    def set_state(self, state: dict[str, Any]) -> None:
        for field, value in state.items():
            setattr(self, field, copy.deepcopy(value))
