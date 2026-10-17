"""Fixed-step, multi-rate simulation engine.

The engine advances in base ticks of ``base_dt`` seconds. Each module runs
every ``interval`` ticks (derived from its ``rate_hz``) and is stepped at the
*end* of its window, so its published output is aligned with the time it
represents. See docs/adr/0003-multi-rate-fixed-step-scheduling.md.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .bus import BusPort, SignalBus
from .module import Module

Observer = Callable[[float, SignalBus], None]


@dataclass
class _Slot:
    module: Module
    port: BusPort
    interval: int


class Engine:
    def __init__(self, base_dt: float = 0.01, strict: bool = True) -> None:
        self.base_dt = base_dt
        self.strict = strict
        self.bus = SignalBus()
        self.tick = 0
        self._slots: list[_Slot] = []
        self._owners: dict[str, str] = {}
        self._observers: list[Observer] = []
        self._started = False

    @property
    def time(self) -> float:
        return self.tick * self.base_dt

    def add(self, module: Module) -> Module:
        if self._started:
            raise RuntimeError("cannot add modules after the simulation has started")
        for key in module.writes:
            if key in self._owners:
                raise ValueError(f"signal {key!r} is already written by {self._owners[key]!r}")
            self._owners[key] = module.name
        interval = max(1, round(1.0 / (module.rate_hz * self.base_dt)))
        port = BusPort(self.bus, module.name, tuple(module.writes))
        self._slots.append(_Slot(module, port, interval))
        return module

    def observe(self, observer: Observer) -> None:
        self._observers.append(observer)

    def unwired_reads(self) -> dict[str, list[str]]:
        """Signals that some module reads but no module writes, mapped to their readers."""
        missing: dict[str, list[str]] = {}
        for slot in self._slots:
            for key in slot.module.reads:
                if key not in self._owners:
                    missing.setdefault(key, []).append(slot.module.name)
        return missing

    def _start(self) -> None:
        missing = self.unwired_reads()
        if self.strict and missing:
            raise ValueError(f"signals read but never written: {missing}")
        for slot in self._slots:
            slot.module.setup(slot.port)
        self.bus.commit()
        self._started = True
        self._notify()

    def step(self) -> None:
        if not self._started:
            self._start()
        t_end = (self.tick + 1) * self.base_dt
        for slot in self._slots:
            if (self.tick + 1) % slot.interval == 0:
                slot.port.time = t_end
                slot.module.step(slot.interval * self.base_dt, slot.port)
        self.bus.commit()
        self.tick += 1
        self._notify()

    def run(self, duration: float) -> None:
        for _ in range(round(duration / self.base_dt)):
            self.step()

    def _notify(self) -> None:
        for observer in self._observers:
            observer(self.time, self.bus)
