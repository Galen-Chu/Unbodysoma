"""The contract every simulated subsystem (body or mind) implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .bus import BusPort


class Module(ABC):
    """A subsystem that advances its own state at a fixed rate.

    Subclasses declare which signals they ``reads`` and ``writes``. The engine
    uses these declarations to enforce a single writer per signal and to
    detect reads that nothing produces.
    """

    name: str = "module"
    rate_hz: float = 10.0
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()

    def setup(self, port: BusPort) -> None:  # noqa: B027 - optional hook
        """Publish initial values. Called once before the first tick."""

    @abstractmethod
    def step(self, dt: float, port: BusPort) -> None:
        """Advance internal state by ``dt`` seconds and publish outputs."""
