"""Double-buffered signal bus: the only channel through which modules talk.

Modules read values committed at the end of the previous tick and write into
a pending buffer. ``commit()`` publishes all pending writes at once, so the
result of a tick never depends on the order in which modules were stepped.
See docs/adr/0002-double-buffered-signal-bus.md.
"""

from __future__ import annotations


class SignalBus:
    def __init__(self) -> None:
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
        self._committed = dict(signals)
        self._pending.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._committed


class BusPort:
    """A module's restricted view of the bus: it may only write keys it declared."""

    def __init__(self, bus: SignalBus, owner: str, writes: tuple[str, ...]) -> None:
        self._bus = bus
        self._owner = owner
        self._writes = frozenset(writes)
        # Simulation time (s) at the end of the step currently being computed.
        self.time = 0.0

    def read(self, key: str, default: float = 0.0) -> float:
        return self._bus.read(key, default)

    def write(self, key: str, value: float) -> None:
        if key not in self._writes:
            raise PermissionError(f"module {self._owner!r} wrote undeclared signal {key!r}")
        self._bus.write(key, value)
