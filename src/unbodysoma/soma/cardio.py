"""Cardiovascular system — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

import math
import random

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, ou_step, relax


class Cardio(Module):
    """Heart rate driven by adrenaline and physical exertion, with heart-rate variability.

    The mean level relaxes toward ``resting + k_adr * adrenaline + k_ex * exertion``.
    On top of it sit two kinds of beat-to-beat variability (HRV):

    - respiratory sinus arrhythmia (RSA): a sinusoid at the breathing rate;
    - slow fluctuation: an Ornstein-Uhlenbeck process (LF-band-like).

    Adrenaline suppresses both, as sympathetic activation reduces HRV in real
    bodies. No pressure, volume or baroreflex yet.
    """

    name = "soma.cardio"
    rate_hz = 10.0
    reads = ("soma.endocrine.adrenaline", "motor.exertion", "motor.sleeping")
    signal_specs = (SignalSpec("soma.cardio.heart_rate", "bpm", 0.0, 300.0, "Heart rate"),)
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("resting_bpm", 65.0, "bpm", 30.0, 120.0, "Resting heart rate"),
        ParamSpec("max_bpm", 190.0, "bpm", 100.0, 230.0, "Ceiling of the heart-rate response"),
        ParamSpec("k_adrenaline", 40.0, "bpm", 0.0, 150.0, "Heart-rate gain per unit adrenaline"),
        ParamSpec("k_exertion", 70.0, "bpm", 0.0, 150.0, "Heart-rate gain per unit exertion"),
        ParamSpec("tau", 5.0, "s", 0.1, 120.0, "Time constant of heart-rate changes"),
        ParamSpec("sleep_bpm_drop", 8.0, "bpm", 0.0, 30.0, "Fall of the resting heart rate during sleep"),
        ParamSpec("rsa_amplitude", 3.0, "bpm", 0.0, 20.0, "Respiratory sinus arrhythmia amplitude at rest"),
        ParamSpec("respiration_hz", 0.25, "Hz", 0.05, 1.0, "Breathing rate that paces the RSA"),
        ParamSpec("lf_sigma", 2.0, "bpm", 0.0, 20.0, "SD of slow heart-rate fluctuation at rest"),
        ParamSpec("lf_tau", 10.0, "s", 0.5, 300.0, "Correlation time of slow heart-rate fluctuation"),
        ParamSpec("hrv_suppression", 0.8, "", 0.0, 1.0, "Share of HRV removed at full adrenaline"),
        ParamSpec("seed", 2, "", 0, math.inf, "Random seed of the fluctuation", source="run setting"),
    )
    state_fields = ("heart_rate", "lf", "_rng")

    def __init__(
        self,
        resting_bpm: float = 65.0,
        max_bpm: float = 190.0,
        k_adrenaline: float = 40.0,
        k_exertion: float = 70.0,
        tau: float = 5.0,
        sleep_bpm_drop: float = 8.0,
        rsa_amplitude: float = 3.0,
        respiration_hz: float = 0.25,
        lf_sigma: float = 2.0,
        lf_tau: float = 10.0,
        hrv_suppression: float = 0.8,
        seed: int = 2,
    ) -> None:
        self.resting_bpm = resting_bpm
        self.max_bpm = max_bpm
        self.k_adrenaline = k_adrenaline
        self.k_exertion = k_exertion
        self.tau = tau
        self.sleep_bpm_drop = sleep_bpm_drop
        self.rsa_amplitude = rsa_amplitude
        self.respiration_hz = respiration_hz
        self.lf_sigma = lf_sigma
        self.lf_tau = lf_tau
        self.hrv_suppression = hrv_suppression
        self.seed = seed
        self._rng = random.Random(seed)
        self.heart_rate = resting_bpm  # mean level, without variability
        self.lf = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("soma.cardio.heart_rate", self.heart_rate)

    def step(self, dt: float, port: BusPort) -> None:
        adrenaline = port.read("soma.endocrine.adrenaline")
        floor = self.resting_bpm - self.sleep_bpm_drop * port.read("motor.sleeping")
        target = floor + self.k_adrenaline * adrenaline + self.k_exertion * port.read("motor.exertion")
        self.heart_rate = relax(self.heart_rate, clamp(target, floor, self.max_bpm), dt, self.tau)

        self.lf = ou_step(self.lf, dt, self.lf_tau, self.lf_sigma, self._rng)
        rsa = self.rsa_amplitude * math.sin(2.0 * math.pi * self.respiration_hz * port.time)
        variability = (1.0 - self.hrv_suppression * adrenaline) * (rsa + self.lf)
        port.write("soma.cardio.heart_rate", clamp(self.heart_rate + variability, 0.0, self.max_bpm))
