"""Analysis metrics: heart-rate variability and distribution-level comparisons.

The distribution metrics implement the acceptance measures proposed in
docs/VARIABILITY.md §6: they compare *distributions*, not just averages.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from statistics import mean, pstdev

# -- heart-rate variability ---------------------------------------------------


def rr_intervals(times: Sequence[float], heart_rate: Sequence[float]) -> list[float]:
    """Beat-to-beat (RR) intervals in seconds, reconstructed from a sampled heart-rate trace.

    Integrates the beat phase (HR / 60 beats per second) between samples and
    records a beat each time the phase crosses a whole number.
    """
    if len(times) != len(heart_rate):
        raise ValueError("times and heart_rate must have the same length")
    beats: list[float] = []
    phase = 0.0
    for i in range(1, len(times)):
        t0, t1 = times[i - 1], times[i]
        rate = heart_rate[i - 1] / 60.0
        new_phase = phase + rate * (t1 - t0)
        while math.floor(new_phase) > math.floor(phase):
            next_beat = math.floor(phase) + 1.0
            beats.append(t0 + (next_beat - phase) / rate)
            phase, t0 = next_beat, beats[-1]
        phase = new_phase
    return [b - a for a, b in zip(beats, beats[1:], strict=False)]


def sdnn_ms(rr: Sequence[float]) -> float:
    """Standard deviation of RR intervals, in ms (overall variability)."""
    return 1000.0 * pstdev(rr)


def rmssd_ms(rr: Sequence[float]) -> float:
    """Root mean square of successive RR differences, in ms (short-term, vagally mediated variability)."""
    diffs = [b - a for a, b in zip(rr, rr[1:], strict=False)]
    return 1000.0 * math.sqrt(mean(d * d for d in diffs))


# -- distributions ------------------------------------------------------------


def distribution(counts: Mapping[str, float]) -> dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("counts must not be all zero")
    return {k: v / total for k, v in counts.items()}


def entropy_bits(probabilities: Mapping[str, float]) -> float:
    """Shannon entropy in bits; 0 for a single certain outcome. Pass counts through ``distribution`` first."""
    if not math.isclose(math.fsum(probabilities.values()), 1.0, abs_tol=1e-9):
        raise ValueError("probabilities must sum to 1 (use distribution() to normalize counts)")
    return -sum(p * math.log2(p) for p in probabilities.values() if p > 0)


def entropy_ratio(simulated: Mapping[str, float], reference: Mapping[str, float]) -> float:
    """H(simulated) / H(reference): < 1 too concentrated (mode collapse), > 1 too spread out."""
    return entropy_bits(distribution(simulated)) / entropy_bits(distribution(reference))


def mode_amplification_ratio(simulated: Mapping[str, float], reference: Mapping[str, float]) -> float:
    """P_sim(reference mode) / P_ref(reference mode); ideally about 1.

    This is the "everyone picks 7" measure: how much more often the simulation
    produces the most common reference outcome than the reference does.
    """
    sim, ref = distribution(simulated), distribution(reference)
    mode = max(ref, key=lambda k: ref[k])
    return sim.get(mode, 0.0) / ref[mode]
