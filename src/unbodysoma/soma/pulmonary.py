"""Respiratory system — L1-lite (docs/SOMA.md §2.8).

Ventilation tracks the metabolic drive: breathing rate and minute
ventilation scale with exertion (and mildly with adrenergic arousal), and
arterial oxygen saturation stays in the healthy band, dipping a little at
heavy exertion. Anchors: normal adult resting rate 12–20 breaths/min and
the clinical worry threshold of 25 (Cretikos et al., 2008); target SpO₂
94–98 % for most adults (O'Driscoll et al., 2008). No CO₂ chemistry or
hypoxic world events yet — the module is a prepared interface for
suffocation, panic and emotion-regulation work (PSYCHE.md).
"""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax


class Respiration(Module):
    """Breathing rate, minute ventilation and arterial oxygen saturation.

    Nothing reads these signals yet — as with cortisol before Phase 3, this
    is a prepared slow interface; the cardiovascular RSA still paces at its
    own fixed breathing rate until the two modules are coupled.
    """

    name = "soma.respiration"
    rate_hz = 1.0
    reads = ("motor.exertion", "motor.sleeping", "soma.endocrine.adrenaline")
    signal_specs = (
        SignalSpec("soma.respiration.rate", "breaths/min", 4.0, 60.0, "Breathing rate"),
        SignalSpec("soma.respiration.minute_ventilation", "L/min", 2.0, 120.0, "Minute ventilation"),
        SignalSpec("soma.respiration.spo2", "%", 70.0, 100.0, "Arterial oxygen saturation"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "resting_rate",
            14.0,
            "breaths/min",
            8.0,
            25.0,
            "Breathing rate at rest",
            source="Cretikos et al. (2008): normal adult range 12–20/min",
        ),
        ParamSpec(
            "exertion_rate_gain",
            1.2,
            "breaths/min per exertion",
            0.0,
            4.0,
            "Breathing rate added per unit exertion, relative to rest",
            source="calibrated: moderate exercise reaches the mid-20s to 30s",
        ),
        ParamSpec("adrenaline_rate_gain", 4.0, "breaths/min", 0.0, 20.0, "Breathing rate added at full adrenaline"),
        ParamSpec(
            "sleep_rate_factor",
            0.85,
            "",
            0.5,
            1.0,
            "Breathing rate during sleep, relative to rest",
            source="sleep lowers ventilation; calibrated",
        ),
        ParamSpec(
            "resting_ventilation",
            6.0,
            "L/min",
            3.0,
            12.0,
            "Minute ventilation at rest",
            source="typical adult resting ventilation ≈ 6 L/min",
        ),
        ParamSpec(
            "exertion_ventilation_gain",
            26.0,
            "L/min per exertion",
            0.0,
            100.0,
            "Minute ventilation added per unit exertion",
            source="calibrated: moderate exercise ≈ 3–5 × rest",
        ),
        ParamSpec(
            "resting_spo2",
            97.5,
            "%",
            94.0,
            100.0,
            "Arterial saturation at rest",
            source="O'Driscoll et al. (2008): target range 94–98 %",
        ),
        ParamSpec(
            "exertion_spo2_dip",
            2.5,
            "%",
            0.0,
            8.0,
            "Saturation dip at full exertion (healthy exercise desaturation is small)",
            source="calibrated: healthy adults stay ≥ 94 % during moderate exercise",
        ),
        ParamSpec("rate_tau", 10.0, "s", 1.0, 300.0, "Time constant of breathing-rate changes"),
        ParamSpec("ventilation_tau", 15.0, "s", 1.0, 300.0, "Time constant of ventilation changes"),
    )
    state_fields = ("rate", "ventilation", "spo2")

    def __init__(
        self,
        resting_rate: float = 14.0,
        exertion_rate_gain: float = 1.2,
        adrenaline_rate_gain: float = 4.0,
        sleep_rate_factor: float = 0.85,
        resting_ventilation: float = 6.0,
        exertion_ventilation_gain: float = 26.0,
        resting_spo2: float = 97.5,
        exertion_spo2_dip: float = 2.5,
        rate_tau: float = 10.0,
        ventilation_tau: float = 15.0,
    ) -> None:
        self.resting_rate = resting_rate
        self.exertion_rate_gain = exertion_rate_gain
        self.adrenaline_rate_gain = adrenaline_rate_gain
        self.sleep_rate_factor = sleep_rate_factor
        self.resting_ventilation = resting_ventilation
        self.exertion_ventilation_gain = exertion_ventilation_gain
        self.resting_spo2 = resting_spo2
        self.exertion_spo2_dip = exertion_spo2_dip
        self.rate_tau = rate_tau
        self.ventilation_tau = ventilation_tau
        self.rate = resting_rate
        self.ventilation = resting_ventilation
        self.spo2 = resting_spo2

    def setup(self, port: BusPort) -> None:
        port.write("soma.respiration.rate", self.rate)
        port.write("soma.respiration.minute_ventilation", self.ventilation)
        port.write("soma.respiration.spo2", self.spo2)

    def step(self, dt: float, port: BusPort) -> None:
        exertion = port.read("motor.exertion")
        adrenaline = port.read("soma.endocrine.adrenaline")
        sleeping = port.read("motor.sleeping") > 0.5

        rest = self.resting_rate * (self.sleep_rate_factor if sleeping else 1.0)
        rate_target = clamp(
            rest + self.resting_rate * self.exertion_rate_gain * exertion + self.adrenaline_rate_gain * adrenaline,
            4.0,
            60.0,
        )
        ventilation_target = clamp(
            self.resting_ventilation * (self.sleep_rate_factor if sleeping else 1.0)
            + self.exertion_ventilation_gain * exertion
            + 2.0 * adrenaline,
            2.0,
            120.0,
        )
        spo2_target = clamp(
            self.resting_spo2 - self.exertion_spo2_dip * exertion * exertion + 0.5 * sleeping,
            70.0,
            100.0,
        )
        self.rate = relax(self.rate, rate_target, dt, self.rate_tau)
        self.ventilation = relax(self.ventilation, ventilation_target, dt, self.ventilation_tau)
        self.spo2 = relax(self.spo2, spo2_target, dt, self.rate_tau)

        port.write("soma.respiration.rate", self.rate)
        port.write("soma.respiration.minute_ventilation", self.ventilation)
        port.write("soma.respiration.spo2", self.spo2)
