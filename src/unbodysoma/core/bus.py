"""Double-buffered signal bus: the only channel through which modules talk.

Modules read values committed at the end of the previous tick and write into
a pending buffer. ``commit()`` publishes all pending writes at once, so the
result of a tick never depends on the order in which modules were stepped.
See docs/adr/0002-double-buffered-signal-bus.md.
"""

from __future__ import annotations


class SignalBus:
    def __init__(self) -> None:
        # Both dicts are only ever mutated in place, never rebound: ports and
        # readers hold direct references to them to keep the hot path short.
        self._committed: dict[str, float] = {}
        self._pending: dict[str, float] = {}

    def read(self, key: str, default: float = 0.0) -> float:
        return self._committed.get(key, default)

    def write(self, key: str, value: float) -> None:
        self._pending[key] = float(value)

    def commit(self) -> None:
        self._committed.update(self._pending)
        self._pending.clear()

    def snapshot(self) -> dict[str, float]:
        return dict(self._committed)

    def restore(self, signals: dict[str, float]) -> None:
        self._committed.clear()
        self._committed.update(signals)
        self._pending.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._committed


class BusReader:
    """Read-only view of a bus, handed to observers and breakpoints (ADR-0005).

    It has no ``write`` method, so an observer cannot change a run by accident.
    """

    __slots__ = ("_committed",)

    def __init__(self, bus: SignalBus) -> None:
        self._committed = bus._committed

    def read(self, key: str, default: float = 0.0) -> float:
        return self._committed.get(key, default)

    def snapshot(self) -> dict[str, float]:
        return dict(self._committed)

    def __contains__(self, key: str) -> bool:
        return key in self._committed


class BusPort:
    """A module's restricted view of the bus: it may only write keys it declared."""

    __slots__ = ("_committed", "_pending", "_owner", "_writes", "time")

    def __init__(self, bus: SignalBus, owner: str, writes: tuple[str, ...]) -> None:
        self._committed = bus._committed
        self._pending = bus._pending
        self._owner = owner
        self._writes = frozenset(writes)
        # Simulation time (s) at the end of the step currently being computed.
        self.time = 0.0

    def read(self, key: str, default: float = 0.0) -> float:
        return self._committed.get(key, default)

    def write(self, key: str, value: float) -> None:
        if key not in self._writes:
            raise PermissionError(f"module {self._owner!r} wrote undeclared signal {key!r}")
        self._pending[key] = float(value)
