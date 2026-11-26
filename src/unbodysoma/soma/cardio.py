"""Cardiovascular system — L1 rate kinetics and ceiling (docs/SOMA.md §2.1).

Heart rate rises through two pathways with distinct kinetics: a fast neural
response (vagal withdrawal and sympathetic drive — adrenaline and the first
beat-to-beat jump of exercise) and a slow metabolic response (cardiac output
matching the working muscle, Whipp & Wasserman, 1972). The ceiling scales
with age as 208 − 0.7 × age (Tanaka, Monahan & Seals, 2001). Recovery is
slower than onset, calibrated so the 1-minute post-exercise drop meets the
healthy criterion of Cole et al. (1999). No pressure, volume or baroreflex
yet.
"""

from __future__ import annotations

import math
import random

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, ou_step, relax


class Cardio(Module):
    """Heart rate driven by adrenaline and physical exertion, with heart-rate variability.

    The fast level relaxes (seconds) toward
    ``resting + k_adrenaline * adrenaline + fast_share * k_exertion * exertion``;
    the slow level follows the rest of the exertion response with exercise
    on-kinetics (tens of seconds up, slower down). On top of the mean sit two
    kinds of beat-to-beat variability (HRV): respiratory sinus arrhythmia and
    a slow Ornstein-Uhlenbeck fluctuation, both suppressed by adrenaline as
    sympathetic activation reduces HRV in real bodies.
    """

    name = "soma.cardio"
    rate_hz = 10.0
    reads = ("soma.endocrine.adrenaline", "motor.exertion", "motor.sleeping", "soma.respiration.rate")
    signal_specs = (SignalSpec("soma.cardio.heart_rate", "bpm", 0.0, 300.0, "Heart rate"),)
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("resting_bpm", 65.0, "bpm", 30.0, 120.0, "Resting heart rate"),
        ParamSpec(
            "age_years",
            35.0,
            "years",
            5.0,
            100.0,
            "Chronological age (scales the maximal heart rate)",
            source="Tanaka et al. (2001): HR_max = 208 − 0.7 × age",
        ),
        ParamSpec("k_adrenaline", 40.0, "bpm", 0.0, 150.0, "Heart-rate gain per unit adrenaline"),
        ParamSpec("k_exertion", 70.0, "bpm", 0.0, 150.0, "Heart-rate gain per unit exertion"),
        ParamSpec(
            "tau",
            5.0,
            "s",
            0.1,
            120.0,
            "Time constant of the fast (neural) heart-rate response",
        ),
        ParamSpec(
            "fast_exertion_share",
            0.25,
            "",
            0.0,
            1.0,
            "Share of the exercise response carried by the fast path",
            source="calibrated: central command / vagal withdrawal cover the initial jump",
        ),
        ParamSpec(
            "exertion_tau_rise",
            40.0,
            "s",
            5.0,
            300.0,
            "Time constant of the rising exercise response (fundamental component)",
            source="Whipp & Wasserman (1972): τ ≈ 20–45 s",
        ),
        ParamSpec(
            "exertion_tau_fall",
            60.0,
            "s",
            5.0,
            600.0,
            "Time constant of heart-rate recovery after exercise",
            source="calibrated: the 1-min recovery meets Cole et al. (1999)",
        ),
        ParamSpec("sleep_bpm_drop", 8.0, "bpm", 0.0, 30.0, "Fall of the resting heart rate during sleep"),
        ParamSpec("rsa_amplitude", 3.0, "bpm", 0.0, 20.0, "Respiratory sinus arrhythmia amplitude at rest"),
        ParamSpec(
            "rsa_rest_rate",
            14.0,
            "breaths/min",
            8.0,
            25.0,
            "Breathing rate the RSA amplitude is quoted at (faster breathing shrinks it)",
            source="RSA amplitude falls as breathing rate rises, as observed in exercise",
        ),
        ParamSpec("lf_sigma", 2.0, "bpm", 0.0, 20.0, "SD of slow heart-rate fluctuation at rest"),
        ParamSpec("lf_tau", 10.0, "s", 0.5, 300.0, "Correlation time of slow heart-rate fluctuation"),
        ParamSpec("hrv_suppression", 0.8, "", 0.0, 1.0, "Share of HRV removed at full adrenaline"),
        ParamSpec("seed", 2, "", 0, math.inf, "Random seed of the fluctuation", source="run setting"),
    )
    state_fields = ("heart_rate", "slow", "lf", "rsa_phase", "_rng")

    def __init__(
        self,
        resting_bpm: float = 65.0,
        age_years: float = 35.0,
        k_adrenaline: float = 40.0,
        k_exertion: float = 70.0,
        tau: float = 5.0,
        fast_exertion_share: float = 0.25,
        exertion_tau_rise: float = 40.0,
        exertion_tau_fall: float = 60.0,
        sleep_bpm_drop: float = 8.0,
        rsa_amplitude: float = 3.0,
        rsa_rest_rate: float = 14.0,
        lf_sigma: float = 2.0,
        lf_tau: float = 10.0,
        hrv_suppression: float = 0.8,
        seed: int = 2,
    ) -> None:
        self.resting_bpm = resting_bpm
        self.age_years = age_years
        self.k_adrenaline = k_adrenaline
        self.k_exertion = k_exertion
        self.tau = tau
        self.fast_exertion_share = fast_exertion_share
        self.exertion_tau_rise = exertion_tau_rise
        self.exertion_tau_fall = exertion_tau_fall
        self.sleep_bpm_drop = sleep_bpm_drop
        self.rsa_amplitude = rsa_amplitude
        self.rsa_rest_rate = rsa_rest_rate
        self.lf_sigma = lf_sigma
        self.lf_tau = lf_tau
        self.hrv_suppression = hrv_suppression
        self.seed = seed
        self._rng = random.Random(seed)
        self.heart_rate = resting_bpm  # fast level, without variability
        self.slow = 0.0
        self.lf = 0.0
        self.rsa_phase = 0.0

    @property
    def hr_max(self) -> float:
        return 208.0 - 0.7 * self.age_years

    def setup(self, port: BusPort) -> None:
        port.write("soma.cardio.heart_rate", self.heart_rate)

    def step(self, dt: float, port: BusPort) -> None:
        adrenaline = port.read("soma.endocrine.adrenaline")
        exertion = port.read("motor.exertion")
        floor = self.resting_bpm - self.sleep_bpm_drop * port.read("motor.sleeping")

        fast_target = floor + self.k_adrenaline * adrenaline + self.fast_exertion_share * self.k_exertion * exertion
        self.heart_rate = relax(self.heart_rate, clamp(fast_target, floor, self.hr_max), dt, self.tau)

        # The slow metabolic path gets whatever headroom the ceiling leaves.
        slow_target = min((1.0 - self.fast_exertion_share) * self.k_exertion * exertion, self.hr_max - self.heart_rate)
        rise = slow_target > self.slow
        self.slow = relax(
            self.slow, max(slow_target, 0.0), dt, self.exertion_tau_rise if rise else self.exertion_tau_fall
        )

        self.lf = ou_step(self.lf, dt, self.lf_tau, self.lf_sigma, self._rng)
        # RSA is paced by the actual breathing rate (phase integrated, so rate
        # changes do not jump the phase) and its amplitude shrinks as breathing
        # speeds up, as in exercise.
        rate = max(port.read("soma.respiration.rate"), 1.0)
        self.rsa_phase += 2.0 * math.pi * (rate / 60.0) * dt
        rsa = self.rsa_amplitude * clamp(self.rsa_rest_rate / rate, 0.3, 1.2) * math.sin(self.rsa_phase)
        variability = (1.0 - self.hrv_suppression * adrenaline) * (rsa + self.lf)
        mean = clamp(self.heart_rate + self.slow, floor, self.hr_max)
        port.write("soma.cardio.heart_rate", clamp(mean + variability, 0.0, self.hr_max))
