"""Fixed-step, multi-rate simulation engine.

The engine advances in base ticks of ``base_dt`` seconds. Each module runs
every ``interval`` ticks (derived from its ``rate_hz``) and is stepped at the
*end* of its window, so its published output is aligned with the time it
represents. See docs/adr/0003-multi-rate-fixed-step-scheduling.md.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .bus import BusPort, SignalBus
from .interventions import LESION_MODES, Clamp, Intervention, Lesion
from .module import Module

Observer = Callable[[float, SignalBus], None]
EventListener = Callable[[dict[str, Any]], None]
StopCondition = Callable[[SignalBus], bool]


@dataclass
class _Slot:
    module: Module
    port: BusPort
    interval: int


@dataclass(frozen=True)
class Snapshot:
    """Complete simulation state at a tick boundary. See docs/adr/0004-explicit-module-state.md."""

    tick: int
    signals: dict[str, float]
    modules: dict[str, dict[str, Any]]
    active_interventions: frozenset[int] = field(default_factory=frozenset)


class Engine:
    def __init__(self, base_dt: float = 0.01, strict: bool = True) -> None:
        self.base_dt = base_dt
        self.strict = strict
        self.bus = SignalBus()
        self.tick = 0
        self.events: list[dict[str, Any]] = []
        self._slots: list[_Slot] = []
        self._owners: dict[str, str] = {}
        self._observers: list[Observer] = []
        self._event_listeners: list[EventListener] = []
        self._stop_reason: str | None = None
        self._interventions: list[Intervention] = []
        self._active_ids: frozenset[int] = frozenset()
        self._next_intervention_id = 1
        self._started = False

    @property
    def time(self) -> float:
        return self.tick * self.base_dt

    @property
    def modules(self) -> list[Module]:
        return [slot.module for slot in self._slots]

    def signals(self) -> list[str]:
        """All declared output signals, sorted."""
        return sorted(self._owners)

    # -- assembly ---------------------------------------------------------

    def add(self, module: Module) -> Module:
        if self._started:
            raise RuntimeError("cannot add modules after the simulation has started")
        if any(slot.module.name == module.name for slot in self._slots):
            raise ValueError(f"a module named {module.name!r} is already registered")
        for key in module.writes:
            if key in self._owners:
                raise ValueError(f"signal {key!r} is already written by {self._owners[key]!r}")
            self._owners[key] = module.name
        interval = max(1, round(1.0 / (module.rate_hz * self.base_dt)))
        port = BusPort(self.bus, module.name, tuple(module.writes))
        self._slots.append(_Slot(module, port, interval))
        return module

    def observe(self, observer: Observer) -> None:
        """Call ``observer(t, bus)`` after setup and after every tick. Observers must not write."""
        self._observers.append(observer)

    def on_event(self, listener: EventListener) -> None:
        self._event_listeners.append(listener)

    def unwired_reads(self) -> dict[str, list[str]]:
        """Signals that some module reads but no module writes, mapped to their readers."""
        missing: dict[str, list[str]] = {}
        for slot in self._slots:
            for key in slot.module.reads:
                if key not in self._owners:
                    missing.setdefault(key, []).append(slot.module.name)
        return missing

    # -- running ----------------------------------------------------------

    def _start(self) -> None:
        missing = self.unwired_reads()
        if self.strict and missing:
            raise ValueError(f"signals read but never written: {missing}")
        for slot in self._slots:
            slot.module.setup(slot.port)
        self._apply_interventions(self._active_at(0.0))
        self.bus.commit()
        self._started = True
        self._log_transitions(self._active_at(0.0), 0.0)
        self._notify()

    def step(self) -> None:
        if not self._started:
            self._start()
        t_end = (self.tick + 1) * self.base_dt
        active = self._active_at(t_end)
        lesioned = {iv.module for iv in active if isinstance(iv, Lesion)}
        for slot in self._slots:
            if slot.module.name not in lesioned and (self.tick + 1) % slot.interval == 0:
                slot.port.time = t_end
                slot.module.step(slot.interval * self.base_dt, slot.port)
        self._apply_interventions(active)
        self.bus.commit()
        self.tick += 1
        self._log_transitions(active, t_end)
        self._notify()

    def run(self, duration: float, until: StopCondition | None = None) -> str | None:
        """Advance ``duration`` seconds. Returns the stop reason if stopped early, else ``None``.

        ``until(bus)`` is a breakpoint checked after every tick; observers can
        also stop the run with ``request_stop``.
        """
        for _ in range(round(duration / self.base_dt)):
            self.step()
            if self._stop_reason is None and until is not None and until(self.bus):
                self._stop_reason = "breakpoint"
            if self._stop_reason is not None:
                reason, self._stop_reason = self._stop_reason, None
                self.record_event("engine.stopped", reason=reason)
                return reason
        return None

    def request_stop(self, reason: str) -> None:
        """Ask ``run`` to return after the current tick (e.g. from a health monitor)."""
        if self._stop_reason is None:
            self._stop_reason = reason

    def record_event(self, kind: str, t: float | None = None, **data: Any) -> None:
        event = {"t": self.time if t is None else t, "kind": kind, **data}
        self.events.append(event)
        for listener in self._event_listeners:
            listener(event)

    def _notify(self) -> None:
        for observer in self._observers:
            observer(self.time, self.bus)

    # -- interventions ----------------------------------------------------

    def clamp(self, key: str, value: float, start: float = 0.0, end: float = math.inf) -> Clamp:
        """Force signal ``key`` to ``value`` during ``start <= t < end``."""
        known = key in self._owners or any(key in slot.module.reads for slot in self._slots)
        if not known:
            raise ValueError(f"unknown signal {key!r}")
        return self._schedule(Clamp(self._next_intervention_id, key, float(value), start, end))

    def lesion(self, module: str, start: float = 0.0, end: float = math.inf, mode: str = "silence") -> Lesion:
        """Disable ``module`` during ``start <= t < end`` (``mode`` is "silence" or "freeze")."""
        if all(slot.module.name != module for slot in self._slots):
            raise ValueError(f"unknown module {module!r}")
        if mode not in LESION_MODES:
            raise ValueError(f"lesion mode must be one of {LESION_MODES}")
        return self._schedule(Lesion(self._next_intervention_id, module, start, end, mode))

    def cancel(self, intervention: Intervention) -> None:
        self._interventions.remove(intervention)
        self.record_event("intervention.cancelled", **intervention.describe())

    @property
    def interventions(self) -> list[Intervention]:
        return list(self._interventions)

    def _schedule(self, intervention: Intervention) -> Intervention:
        if intervention.end <= intervention.start:
            raise ValueError("intervention must end after it starts")
        self._next_intervention_id += 1
        self._interventions.append(intervention)
        self.record_event("intervention.scheduled", **intervention.describe())
        return intervention

    def _active_at(self, t: float) -> list[Intervention]:
        return [iv for iv in self._interventions if iv.active(t)]

    def _apply_interventions(self, active: list[Intervention]) -> None:
        """Write intervention effects into the pending buffer, after modules have written theirs."""
        for iv in active:
            if isinstance(iv, Lesion) and iv.mode == "silence":
                for key in next(s.module.writes for s in self._slots if s.module.name == iv.module):
                    self.bus.write(key, 0.0)
        for iv in active:
            if isinstance(iv, Clamp):
                self.bus.write(iv.key, iv.value)

    def _log_transitions(self, active: list[Intervention], t: float) -> None:
        ids = frozenset(iv.id for iv in active)
        for iv in active:
            if iv.id not in self._active_ids:
                self.record_event("intervention.started", t=t, **iv.describe())
        for iv in self._interventions:
            if iv.id in self._active_ids and iv.id not in ids:
                self.record_event("intervention.ended", t=t, **iv.describe())
        self._active_ids = ids

    # -- snapshots --------------------------------------------------------

    def snapshot(self) -> Snapshot:
        if not self._started:
            self._start()
        return Snapshot(
            tick=self.tick,
            signals=self.bus.snapshot(),
            modules={slot.module.name: slot.module.get_state() for slot in self._slots},
            active_interventions=self._active_ids,
        )

    def restore(self, snapshot: Snapshot) -> None:
        """Rewind (or fast-forward) to ``snapshot``.

        Scheduled interventions, observers and the event log are left untouched,
        so a restored run can be branched with a different set of interventions.
        """
        if not self._started:
            self._start()
        names = {slot.module.name for slot in self._slots}
        if names != set(snapshot.modules):
            raise ValueError("snapshot was taken from an engine with different modules")
        self.tick = snapshot.tick
        self.bus.restore(snapshot.signals)
        for slot in self._slots:
            slot.module.set_state(snapshot.modules[slot.module.name])
        self._active_ids = snapshot.active_interventions
