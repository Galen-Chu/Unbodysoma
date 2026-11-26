"""Place memory: where it hurt stays dangerous, and steering avoids it.

A coarse grid of danger over the world, deposited by felt pain at the
organism's position and decaying over days (a hippocampus-flavoured spatial
memory in its minimal form — the cognitive map is a scalar field, not a
graph; O'Keefe & Nadel, 1978, for the lineage). The module publishes the
danger at the current position and a repulsion vector — the danger mass
within a radius, pushing away — which navigation blends into goal-directed
movement. Threat perception avoids what is *seen*; this avoids what was
*experienced* — the Phase 4 place-avoidance loop. Acceptance:
tests/test_place_memory.py; equations: docs/PSYCHE.md §4.10.
"""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp


class PlaceMemory(Module):
    """A pain-deposited danger field over the world, read back as repulsion."""

    name = "psyche.place_memory"
    rate_hz = 10.0
    reads = ("world.position_x", "world.position_y", "intero.pain")
    signal_specs = (
        SignalSpec("psyche.place_memory.danger", "normalized", 0.0, 1.0, "Learned danger at the current position"),
        SignalSpec("psyche.place_memory.avoid_x", "unit", -1.0, 1.0, "Repulsion from nearby danger (x)"),
        SignalSpec("psyche.place_memory.avoid_y", "unit", -1.0, 1.0, "Repulsion from nearby danger (y)"),
    )
    writes = tuple(s.key for s in signal_specs)
    config_args = ("width", "height")
    params = (
        ParamSpec(
            "deposit_rate",
            0.02,
            "1/s",
            0.0,
            1.0,
            "Danger gained per second of unit pain at the current cell",
            source="calibrated: about a minute of strong pain marks a place for days",
        ),
        ParamSpec(
            "tau_danger",
            259200.0,
            "s",
            3600.0,
            2.6e6,
            "Time constant of danger decay",
            source="days-scale persistence, as in learned place avoidance",
        ),
        ParamSpec(
            "avoid_radius",
            4.0,
            "cells",
            0.5,
            20.0,
            "Distance over which danger repels movement",
        ),
        ParamSpec(
            "tau_pain_trace",
            10.0,
            "s",
            0.5,
            120.0,
            "Trailing average of pain; only pain above it deposits (the rising edge)",
            source="calibrated: the place that hurt is marked, not everywhere the ache was carried",
        ),
    )
    state_fields = ("danger", "pain_trace")

    def __init__(
        self,
        width: float = 20.0,
        height: float = 20.0,
        deposit_rate: float = 0.02,
        tau_danger: float = 259200.0,
        avoid_radius: float = 4.0,
        tau_pain_trace: float = 10.0,
    ) -> None:
        self.width = width
        self.height = height
        self.deposit_rate = deposit_rate
        self.tau_danger = tau_danger
        self.avoid_radius = avoid_radius
        self.tau_pain_trace = tau_pain_trace
        self.danger = [0.0] * (int(width) * int(height))
        self.pain_trace = 0.0

    def _cell(self, x: float, y: float) -> tuple[int, int]:
        return int(x) % int(self.width), int(y) % int(self.height)

    def setup(self, port: BusPort) -> None:
        self._publish(port, 0.0, 0.0, 0.0)

    def step(self, dt: float, port: BusPort) -> None:
        x, y = port.read("world.position_x"), port.read("world.position_y")
        pain = port.read("intero.pain")

        decay = 1.0 - dt / self.tau_danger
        for i in range(len(self.danger)):
            self.danger[i] *= decay
        i, j = self._cell(x, y)
        self.danger[i * int(self.height) + j] = clamp(
            self.danger[i * int(self.height) + j] + self.deposit_rate * pain * dt
        )

        # Repulsion: danger mass within the radius pushes away, nearer and
        # stronger cells more.
        ax = ay = 0.0
        radius = self.avoid_radius
        for ci in range(int(x - radius), int(x + radius) + 1):
            for cj in range(int(y - radius), int(y + radius) + 1):
                wi, wj = ci % int(self.width), cj % int(self.height)
                d = self.danger[wi * int(self.height) + wj]
                if d <= 0.0:
                    continue
                # Torus-aware offset from the organism to the danger cell.
                ox = (ci + 0.5 - x + self.width / 2) % self.width - self.width / 2
                oy = (cj + 0.5 - y + self.height / 2) % self.height - self.height / 2
                dist = math.hypot(ox, oy)
                if dist < 0.5 or dist > radius:
                    continue
                weight = d / (dist * dist)
                ax -= weight * ox / dist
                ay -= weight * oy / dist
        here = self.danger[i * int(self.height) + j]
        self._publish(port, here, clamp(ax, -1.0, 1.0), clamp(ay, -1.0, 1.0))

    def _publish(self, port: BusPort, danger: float, ax: float, ay: float) -> None:
        port.write("psyche.place_memory.danger", danger)
        port.write("psyche.place_memory.avoid_x", ax)
        port.write("psyche.place_memory.avoid_y", ay)
