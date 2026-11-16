"""Spectral HRV validation: the Task Force (1996) LF and HF bands.

Synthetic checks pin the band separation; an organism check pins the
physiology: at rest the HF band (respiratory sinus arrhythmia) dominates,
and sympathetic activation suppresses total spectral power.
"""

from __future__ import annotations

import math

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.observe.metrics import band_powers, lf_hf_ratio, rr_intervals
from unbodysoma.world import Event


def synthetic_rr(freq: float, amplitude_ms: float = 40.0, base_s: float = 0.8, beats: int = 240) -> list[float]:
    """An RR series modulated at ``freq`` Hz (as RSA would modulate it)."""
    return [base_s + (amplitude_ms / 1000.0) * math.sin(2 * math.pi * freq * i * base_s) for i in range(beats)]


def test_hf_band_captures_a_025_hz_oscillation():
    lf, hf = band_powers(synthetic_rr(0.25))
    assert hf > 5.0 * lf


def test_lf_band_captures_a_010_hz_oscillation():
    lf, hf = band_powers(synthetic_rr(0.10))
    assert lf > 5.0 * hf


def test_bands_separate_neighbouring_frequencies():
    # just below and just above the 0.15 Hz boundary land in different bands
    _, hf_below = band_powers(synthetic_rr(0.13))
    lf_above, _ = band_powers(synthetic_rr(0.17))
    assert hf_below > 0.0 and lf_above > 0.0


def run_rest(seconds: float = 300.0, threat: bool = False) -> list[float]:
    events = [Event(0.0, 1e9, "world.threat", 0.9)] if threat else []
    engine: Engine = build_minimal_human(events, seed=0)
    recorder = Recorder(("soma.cardio.heart_rate",), every=1.0)
    engine.observe(recorder)
    engine.run(seconds)
    return rr_intervals(recorder.times(), recorder.column("soma.cardio.heart_rate"))


def test_at_rest_hf_dominates_the_ratio():
    ratio = lf_hf_ratio(run_rest())
    assert ratio < 1.0  # RSA (0.25 Hz) sits in the HF band


def test_sympathetic_activation_suppresses_hf_power():
    """Vagal (HF) power collapses under threat, as the Task Force physiology says.

    LF power does *not* fall in this engine: sustained flight makes the
    probabilistic action selection switch between fleeing and idling, which
    swings heart rate in the LF band — a behavioral oscillation, not a
    baroreflex. Documented here so nobody "fixes" the test by accident.
    """
    _, rest_hf = band_powers(run_rest())
    _, stressed_hf = band_powers(run_rest(threat=True))
    assert stressed_hf < 0.5 * rest_hf
